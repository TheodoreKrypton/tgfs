import asyncio
from typing import Tuple, List
from fastapi import Request

from dataclasses import dataclass, field
import xml.etree.ElementTree as ET

from asgidav.folder import Folder
from asgidav.member import Member

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

        body = await request.body()
        content = body.decode("utf-8")
        root = ET.fromstring(content)

        if root.find(".//D:propname", NS_MAP):
            return cls(depth=depth)

        if root.find(".//D:allprop", NS_MAP):
            return cls(depth=depth)

        if root.find(".//D:prop", NS_MAP):
            raise NotImplemented

        return cls(depth=depth)


async def _propstat(member: Member, prop_names: Tuple[str, ...]) -> ET.Element:
    root = ET.Element("D:propstat", {"xmlns:D": DAV_NS})

    properties = dict(await member.get_properties())

    prop = ET.SubElement(root, "D:prop")
    for name in set(prop_names) & set(properties.keys()):
        creation = ET.SubElement(prop, f"D:{name}")
        creation.text = str(properties[name])

    status = ET.SubElement(root, "D:status")
    status.text = "HTTP/1.1 200 OK"

    return root


async def _propfind_response(
    member: Member, depth: int, prop_names: Tuple[str, ...]
) -> List[ET.Element]:
    root = ET.Element("D:response")

    href_elem = ET.SubElement(root, "D:href")
    href_elem.text = f"/{member.path}"

    propstat_elem = await _propstat(
        member=member,
        prop_names=prop_names,
    )
    root.append(propstat_elem)

    res = [root]

    if depth > 0 and isinstance(member, Folder):
        for name in await member.member_names():
            if sub_member := await member.member(name):
                res.extend(await _propfind_response(sub_member, depth - 1, prop_names))

    return res


async def propfind(
    members: Tuple[Member, ...], depth: int, prop_names: Tuple[str, ...]
) -> str:
    root = ET.Element("D:multistatus", {"xmlns:D": DAV_NS})

    tasks = []

    for member in members:
        tasks.append(asyncio.create_task(_propfind_response(member, depth, prop_names)))

    task_responses = await asyncio.gather(*tasks)
    for propfind_responses in task_responses:
        for response in propfind_responses:
            root.append(response)

    ET.register_namespace("D", DAV_NS)
    xml_str = ET.tostring(root, encoding="unicode")

    return f'<?xml version="1.0" encoding="utf-8"?>\n{xml_str}'
