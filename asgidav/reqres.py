from dataclasses import dataclass
from typing import List, Tuple
from urllib.parse import quote

import lxml.etree as et
from fastapi import Request
from lxml.etree import _Element as Element

from asgidav.async_map import async_map
from asgidav.folder import Folder
from asgidav.member import Member, Properties, PropertyName, ResourceType

DAV_NS = "DAV:"
NS_MAP = {"D": DAV_NS}


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


async def _propfind_response(
    member: Member, depth: int, prop_names: Tuple[PropertyName, ...], base_path: str
) -> List[Element]:
    root = et.Element(_tag("response"))

    href_elem = et.SubElement(root, _tag("href"))
    href_elem.text = quote(f"{base_path}{member.path}", safe="/")

    propstat_elem = await _propstat(
        member=member,
        prop_names=prop_names,
    )
    root.append(propstat_elem)

    res = [root]

    if not isinstance(member, Folder) or depth == 0:
        return res

    folder: Folder = member

    names = await member.member_names()
    sub_members = await async_map(lambda name: folder.member(name), names)
    propfind_responses = await async_map(
        lambda m: _propfind_response(m, depth - 1, prop_names, base_path),
        (m for m in sub_members if m is not None),
    )
    for sub_response in propfind_responses:
        res.extend(sub_response)

    return res


async def propfind(
    members: Tuple[Member, ...],
    depth: int,
    prop_names: Tuple[PropertyName, ...],
    base_path: str,
) -> str:
    root = et.Element(_tag("multistatus"), nsmap=NS_MAP)

    for propfind_responses in await async_map(
        lambda member: _propfind_response(member, depth, prop_names, base_path), members
    ):
        for response in propfind_responses:
            root.append(response)

    et.register_namespace("D", DAV_NS)
    return et.tostring(root, encoding="unicode")
