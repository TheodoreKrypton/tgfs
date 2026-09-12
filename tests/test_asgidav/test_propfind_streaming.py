import asyncio
from typing import Any, Dict, List, Optional, Tuple

import lxml.etree as et
import pytest

from asgidav.app import create_app
from asgidav.member import Member, PropertyName
from asgidav.reqres import propfind, propfind_stream

from .common import MockFolder, MockResource

LARGE_CHILD_COUNT = 20_000
DAV = "{DAV:}"


class NamedMockResource(MockResource):
    def __init__(self, path: str, name: str):
        super().__init__(path)
        self._name = name

    async def display_name(self) -> str:
        return self._name


class LargeMockFolder(MockFolder):
    """A folder with many children that records how many children were visited."""

    def __init__(self, path: str, count: int = LARGE_CHILD_COUNT):
        super().__init__(path)
        self.count = count
        self._names = tuple(f"child-{i:05d}.txt" for i in range(count))
        self._name_set = frozenset(self._names)
        self.member_calls = 0

    async def member_names(self) -> Tuple[str, ...]:
        return self._names

    async def member(self, path: str) -> Member | None:
        if path not in self._name_set:
            return None
        self.member_calls += 1
        return NamedMockResource(f"{self.path}/{path}", path)


async def _drain(stream) -> bytes:
    return b"".join([chunk async for chunk in stream])


class TestPropfindStream:
    @pytest.mark.asyncio
    async def test_first_chunk_emitted_before_children_are_materialized(self):
        folder = LargeMockFolder("/large")
        stream = propfind_stream(
            (folder,), 1, ("displayname", "resourcetype"), "/webdav"
        )

        first = await anext(stream)
        assert b"multistatus" in first
        assert (
            folder.member_calls == 0
        ), "the XML root must be emitted before any child is visited"

        second = await anext(stream)
        assert b"/webdav/large" in second
        assert b"child-00000.txt" in second
        assert 0 < folder.member_calls < LARGE_CHILD_COUNT // 10, (
            "child responses must be produced in bounded batches, "
            f"but {folder.member_calls} of {LARGE_CHILD_COUNT} children were visited "
            "before the first child response was emitted"
        )

        await stream.aclose()

    @pytest.mark.asyncio
    async def test_full_stream_is_well_formed_and_complete(self):
        folder = LargeMockFolder("/large")

        body = await _drain(
            propfind_stream((folder,), 1, ("displayname", "resourcetype"), "/webdav")
        )

        root = et.fromstring(body)
        assert et.QName(root).localname == "multistatus"

        responses = root.findall(f"{DAV}response")
        assert len(responses) == LARGE_CHILD_COUNT + 1

        hrefs = [r.findtext(f"{DAV}href") for r in responses]
        assert hrefs[0] == "/webdav/large"
        assert hrefs[1] == "/webdav/large/child-00000.txt"
        assert hrefs[-1] == f"/webdav/large/child-{LARGE_CHILD_COUNT - 1:05d}.txt"
        assert folder.member_calls == LARGE_CHILD_COUNT

    @pytest.mark.asyncio
    async def test_stream_matches_string_helper(self):
        folder = MockFolder(
            "/test",
            {
                "file1.txt": MockResource("/test/file1.txt"),
                "sub": MockFolder("/test/sub"),
            },
        )
        props: Tuple[PropertyName, ...] = ("displayname", "resourcetype")

        streamed = await _drain(propfind_stream((folder,), 1, props, "/webdav"))
        buffered = await propfind((folder,), 1, props, "/webdav")

        streamed_root = et.fromstring(streamed)
        buffered_root = et.fromstring(buffered.encode())

        assert [r.findtext(f"{DAV}href") for r in streamed_root] == [
            r.findtext(f"{DAV}href") for r in buffered_root
        ]

    @pytest.mark.asyncio
    async def test_depth_0_does_not_visit_children(self):
        folder = LargeMockFolder("/large", count=10)

        body = await _drain(propfind_stream((folder,), 0, ("displayname",), "/webdav"))

        root = et.fromstring(body)
        responses = root.findall(f"{DAV}response")
        assert len(responses) == 1
        assert responses[0].findtext(f"{DAV}href") == "/webdav/large"
        assert folder.member_calls == 0

    @pytest.mark.asyncio
    async def test_depth_1_does_not_recurse_into_sub_folders(self):
        grandchild = LargeMockFolder("/test/sub", count=5)
        folder = MockFolder("/test", {"sub": grandchild})

        body = await _drain(propfind_stream((folder,), 1, ("displayname",), "/webdav"))

        root = et.fromstring(body)
        assert [r.findtext(f"{DAV}href") for r in root.findall(f"{DAV}response")] == [
            "/webdav/test",
            "/webdav/test/sub",
        ]
        assert grandchild.member_calls == 0

    @pytest.mark.asyncio
    async def test_depth_2_recurses_one_extra_level(self):
        grandchild = LargeMockFolder("/test/sub", count=2)
        folder = MockFolder("/test", {"sub": grandchild})

        body = await _drain(propfind_stream((folder,), 2, ("displayname",), "/webdav"))

        root = et.fromstring(body)
        assert [r.findtext(f"{DAV}href") for r in root.findall(f"{DAV}response")] == [
            "/webdav/test",
            "/webdav/test/sub",
            "/webdav/test/sub/child-00000.txt",
            "/webdav/test/sub/child-00001.txt",
        ]

    @pytest.mark.asyncio
    async def test_only_requested_properties_are_returned(self):
        folder = MockFolder("/test", {"file1.txt": MockResource("/test/file1.txt")})

        body = await _drain(propfind_stream((folder,), 1, ("displayname",), "/webdav"))

        root = et.fromstring(body)
        for response in root.findall(f"{DAV}response"):
            prop = response.find(f"{DAV}propstat/{DAV}prop")
            assert prop is not None
            assert [et.QName(child).localname for child in prop] == ["displayname"]
            assert response.findtext(f"{DAV}propstat/{DAV}status") == "HTTP/1.1 200 OK"

    @pytest.mark.asyncio
    async def test_collection_resourcetype_is_preserved(self):
        folder = MockFolder("/test", {"file1.txt": MockResource("/test/file1.txt")})

        body = await _drain(propfind_stream((folder,), 1, ("resourcetype",), "/webdav"))

        root = et.fromstring(body)
        collection, resource = root.findall(f"{DAV}response")
        assert (
            collection.find(
                f"{DAV}propstat/{DAV}prop/{DAV}resourcetype/{DAV}collection"
            )
            is not None
        )
        assert (
            resource.find(f"{DAV}propstat/{DAV}prop/{DAV}resourcetype/{DAV}collection")
            is None
        )

    @pytest.mark.asyncio
    async def test_empty_members_still_yields_multistatus(self):
        body = await _drain(propfind_stream((), 1, ("displayname",), "/webdav"))

        root = et.fromstring(body)
        assert et.QName(root).localname == "multistatus"
        assert root.findall(f"{DAV}response") == []

    @pytest.mark.asyncio
    async def test_hrefs_are_url_quoted(self):
        folder = MockFolder("/test", {"a b.txt": MockResource("/test/a b.txt")})

        body = await _drain(propfind_stream((folder,), 1, ("displayname",), "/webdav"))

        root = et.fromstring(body)
        assert "/webdav/test/a%20b.txt" in [
            r.findtext(f"{DAV}href") for r in root.findall(f"{DAV}response")
        ]


class TestPropfindRoute:
    @staticmethod
    async def _call(app, path: str, depth: str, probe) -> List[Tuple[Dict, int]]:
        scope: Dict[str, Any] = {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.3"},
            "http_version": "1.1",
            "method": "PROPFIND",
            "scheme": "http",
            "path": path,
            "raw_path": path.encode(),
            "query_string": b"",
            "root_path": "",
            "headers": [
                (b"host", b"testserver"),
                (b"depth", depth.encode()),
                (b"content-length", b"0"),
            ],
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 80),
        }
        events: List[Tuple[Dict, int]] = []
        request_sent = False

        async def receive() -> Dict[str, Any]:
            nonlocal request_sent
            if request_sent:
                # The client stays connected: block like a real server would
                # instead of spinning, until the response task group cancels us.
                await asyncio.Event().wait()
            request_sent = True
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message: Dict[str, Any]) -> None:
            events.append((message, probe()))

        await app(scope, receive, send)
        return events

    @staticmethod
    def _app(folder: Member):
        async def get_member(path: str) -> Optional[Member]:
            return folder if path.strip("/") == "large" else None

        return create_app(get_member, base_path="/webdav")

    @pytest.mark.asyncio
    async def test_route_streams_headers_and_first_chunk_before_iterating_members(self):
        # A few thousand children is enough to fill several stream chunks; the
        # 20k-member case is covered directly against propfind_stream above.
        folder = LargeMockFolder("/large", count=2_000)

        events = await self._call(
            self._app(folder), "/large", "1", lambda: folder.member_calls
        )

        start, visited_at_start = events[0]
        assert start["type"] == "http.response.start"
        assert start["status"] == 207
        assert (
            visited_at_start == 0
        ), "response headers must be sent before any child is visited"

        headers = {k.lower(): v for k, v in start["headers"]}
        assert headers[b"content-type"] == b"application/xml; charset=utf-8"
        assert (
            b"content-length" not in headers
        ), "a streamed response must not be buffered"

        body_events = [e for e in events if e[0]["type"] == "http.response.body"]
        first_body, visited_at_first_body = body_events[0]
        assert b"multistatus" in first_body["body"]
        assert (
            visited_at_first_body == 0
        ), "the first body chunk must be available before the members are iterated"
        assert len(body_events) > 2, "the body must be streamed in multiple chunks"

        body = b"".join(e[0].get("body", b"") for e in body_events)
        root = et.fromstring(body)
        assert et.QName(root).localname == "multistatus"
        assert len(root.findall(f"{DAV}response")) == folder.count + 1

    @pytest.mark.asyncio
    async def test_route_depth_0(self):
        folder = LargeMockFolder("/large", count=10)

        events = await self._call(
            self._app(folder), "/large", "0", lambda: folder.member_calls
        )

        body = b"".join(
            e[0].get("body", b"")
            for e in events
            if e[0]["type"] == "http.response.body"
        )
        root = et.fromstring(body)
        assert len(root.findall(f"{DAV}response")) == 1
        assert folder.member_calls == 0

    @pytest.mark.asyncio
    async def test_route_missing_member_is_not_found(self):
        folder = LargeMockFolder("/large", count=1)

        events = await self._call(
            self._app(folder), "/missing", "1", lambda: folder.member_calls
        )

        assert events[0][0]["type"] == "http.response.start"
        assert events[0][0]["status"] == 404
        assert folder.member_calls == 0
