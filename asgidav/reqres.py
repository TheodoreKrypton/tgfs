from dataclasses import dataclass
from typing import AsyncGenerator, AsyncIterator, List, Tuple
from urllib.parse import quote

import lxml.etree as et
from fastapi import Request
from lxml.etree import _Element as Element

from asgidav.async_map import async_map
from asgidav.folder import Folder
from asgidav.member import Member, Properties, PropertyName, ResourceType

DAV_NS = "DAV:"
NS_MAP = {"D": DAV_NS}

XML_DECLARATION = b'<?xml version="1.0" encoding="utf-8"?>\n'
MULTISTATUS_OPEN = f'<D:multistatus xmlns:D="{DAV_NS}">'.encode()
MULTISTATUS_CLOSE = b"</D:multistatus>"

# How many children of a collection are resolved (and turned into <D:response>
# elements) at a time. Bounds both concurrency and peak memory while walking
# collections with hundreds of thousands of members.
MEMBER_BATCH_SIZE = 100

# Serialized responses are coalesced up to this size before being yielded, so a
# huge collection does not translate into one ASGI message (and one socket
# write) per member.
STREAM_CHUNK_SIZE = 32 * 1024


@dataclass
class PropfindRequest:
    depth: int
    props: Tuple[str, ...] = (
        "displayname",
        "getcontentlength",
        "getcontenttype",
        "getetag",
        "getlastmodified",
        "creationdate",
        "resourcetype",
    )

    @classmethod
    async def from_request(cls, request: Request):
        depth = int(request.headers["Depth"])

        try:
            body = await request.body()
            root = et.fromstring(body)

            if root.find(".//D:propname", NS_MAP) is not None:
                return cls(depth=depth)

            if root.find(".//D:allprop", NS_MAP) is not None:
                return cls(depth=depth)

            if (elem := root.find(".//D:prop", NS_MAP)) is not None:
                requested_props = frozenset(
                    et.QName(prop_elem).localname for prop_elem in elem
                )
                return cls(
                    depth=depth, props=tuple(requested_props.intersection(cls.props))
                )
        except (et.XMLSyntaxError,):
            return cls(depth=depth)


def _tag(name: str) -> str:
    return "{%s}%s" % (DAV_NS, name)


async def _propstat(member: Member, prop_names: Tuple[PropertyName, ...]) -> Element:
    root = et.Element(_tag("propstat"), nsmap=NS_MAP)
    properties: Properties = await member.get_properties()
    props = et.SubElement(root, _tag("prop"))
    for name in set(prop_names) & set(properties.keys()):
        prop = et.SubElement(props, _tag(name))
        if name == "resourcetype" and member.resource_type == ResourceType.COLLECTION:
            et.SubElement(prop, _tag(properties[name]))
        else:
            prop.text = properties[name]

    status = et.SubElement(root, _tag("status"))
    status.text = "HTTP/1.1 200 OK"

    return root


async def _response_element(
    member: Member, prop_names: Tuple[PropertyName, ...], base_path: str
) -> Element:
    root = et.Element(_tag("response"), nsmap=NS_MAP)

    href = et.SubElement(root, _tag("href"))
    href.text = quote(f"{base_path}{member.path}", safe="/")

    root.append(await _propstat(member=member, prop_names=prop_names))

    return root


async def _child_response_elements(
    member: Member, depth: int, prop_names: Tuple[PropertyName, ...], base_path: str
) -> AsyncIterator[Element]:
    """Yield a <D:response> element for every descendant of ``member`` reachable
    within ``depth`` levels.

    Children are resolved in batches of ``MEMBER_BATCH_SIZE`` so that neither the
    member objects nor their response elements are ever all held at once, and so
    that the event loop is handed back regularly while a very large collection is
    enumerated.
    """
    if depth <= 0 or not isinstance(member, Folder):
        return

    folder: Folder = member
    names = tuple(await folder.member_names())

    for start in range(0, len(names), MEMBER_BATCH_SIZE):
        batch = names[start : start + MEMBER_BATCH_SIZE]
        sub_members = [
            m for m in await async_map(folder.member, batch) if m is not None
        ]
        elements = await async_map(
            lambda m: _response_element(m, prop_names, base_path), sub_members
        )

        for sub_member, element in zip(sub_members, elements):
            yield element
            async for sub_element in _child_response_elements(
                sub_member, depth - 1, prop_names, base_path
            ):
                yield sub_element


async def _response_elements(
    member: Member, depth: int, prop_names: Tuple[PropertyName, ...], base_path: str
) -> AsyncIterator[Element]:
    yield await _response_element(member, prop_names, base_path)

    async for element in _child_response_elements(member, depth, prop_names, base_path):
        yield element


async def propfind_stream(
    members: Tuple[Member, ...],
    depth: int,
    prop_names: Tuple[PropertyName, ...],
    base_path: str,
) -> AsyncGenerator[bytes, None]:
    """Stream a `multistatus` document, starting with the XML prologue so the
    response headers and first bytes are on the wire before the members are
    enumerated."""
    yield XML_DECLARATION + MULTISTATUS_OPEN

    buffer: List[bytes] = []
    buffered = 0

    for member in members:
        async for element in _response_elements(member, depth, prop_names, base_path):
            serialized = et.tostring(element, encoding="utf-8", xml_declaration=False)
            buffer.append(serialized)
            buffered += len(serialized)

            if buffered >= STREAM_CHUNK_SIZE:
                yield b"".join(buffer)
                buffer.clear()
                buffered = 0

    if buffer:
        yield b"".join(buffer)

    yield MULTISTATUS_CLOSE


async def propfind(
    members: Tuple[Member, ...],
    depth: int,
    prop_names: Tuple[PropertyName, ...],
    base_path: str,
) -> str:
    """Buffered equivalent of `propfind_stream`, kept for callers that need the
    whole document as a string. Prefer `propfind_stream` for collections whose
    size is not known to be small."""
    root = et.Element(_tag("multistatus"), nsmap=NS_MAP)

    for member in members:
        async for element in _response_elements(member, depth, prop_names, base_path):
            root.append(element)

    et.register_namespace("D", DAV_NS)
    return et.tostring(root, encoding="unicode")
