import pytest
from fastapi import Request
from asgidav.reqres import PropfindRequest, propfind, _propstat, _propfind_response
from .common import MockResource, MockFolder


class TestPropfindRequest:
    @pytest.mark.asyncio
    async def test_from_request_default_depth(self, mocker):
        mock_request = mocker.Mock(spec=Request)
        mock_request.headers = {"Depth": "1"}
        mock_request.body = mocker.AsyncMock(return_value=b"")

        result = await PropfindRequest.from_request(mock_request)

        assert result.depth == 1
        assert result.props == (
            "displayname",
            "getcontentlength",
            "getcontenttype",
            "getetag",
            "getlastmodified",
            "creationdate",
            "resourcetype",
        )

    @pytest.mark.asyncio
    async def test_from_request_with_propname(self, mocker):
        mock_request = mocker.Mock(spec=Request)
        mock_request.headers = {"Depth": "0"}
        mock_request.body = mocker.AsyncMock(
            return_value=b"""<?xml version="1.0"?>
            <D:propfind xmlns:D="DAV:">
                <D:propname/>
            </D:propfind>"""
        )

        result = await PropfindRequest.from_request(mock_request)

        assert result.depth == 0

    @pytest.mark.asyncio
    async def test_from_request_with_allprop(self, mocker):
        mock_request = mocker.Mock(spec=Request)
        mock_request.headers = {"Depth": "1"}
        mock_request.body = mocker.AsyncMock(
            return_value=b"""<?xml version="1.0"?>
            <D:propfind xmlns:D="DAV:">
                <D:allprop/>
            </D:propfind>"""
        )

        result = await PropfindRequest.from_request(mock_request)

        assert result.depth == 1

    @pytest.mark.asyncio
    async def test_from_request_with_specific_props(self, mocker):
        mock_request = mocker.Mock(spec=Request)
        mock_request.headers = {"Depth": "1"}
        mock_request.body = mocker.AsyncMock(
            return_value=b"""<?xml version="1.0"?>
            <D:propfind xmlns:D="DAV:">
                <D:prop>
                    <D:displayname/>
                    <D:getcontentlength/>
                    <D:invalidprop/>
                </D:prop>
            </D:propfind>"""
        )

        result = await PropfindRequest.from_request(mock_request)

        assert result.depth == 1
        assert set(result.props) == {"displayname", "getcontentlength"}

    @pytest.mark.asyncio
    async def test_from_request_invalid_xml(self, mocker):
        mock_request = mocker.Mock(spec=Request)
        mock_request.headers = {"Depth": "0"}
        mock_request.body = mocker.AsyncMock(return_value=b"invalid xml")

        result = await PropfindRequest.from_request(mock_request)

        assert result.depth == 0


class TestPropfindFunctions:
    @pytest.mark.asyncio
    async def test_propstat_resource(self):
        resource = MockResource("/test.txt")
        result = await _propstat(resource, ("displayname", "getcontenttype"))

        assert result.tag.endswith("}propstat")
        # Check that the result contains prop and status elements
        props = result.find(".//{DAV:}prop")
        assert props is not None

        status = result.find(".//{DAV:}status")
        assert status is not None
        assert status.text == "HTTP/1.1 200 OK"

    @pytest.mark.asyncio
    async def test_propstat_folder(self):
        folder = MockFolder("/test")
        result = await _propstat(folder, ("displayname", "resourcetype"))

        assert result.tag.endswith("}propstat")
        props = result.find(".//{DAV:}prop")
        assert props is not None

    @pytest.mark.asyncio
    async def test_propfind_response_resource(self):
        resource = MockResource("/test.txt")
        result = await _propfind_response(resource, 0, ("displayname",), "/webdav")

        assert len(result) == 1
        response = result[0]
        assert response.tag.endswith("}response")

        href = response.find(".//{DAV:}href")
        assert href is not None
        assert href.text == "/webdav/test.txt"

    @pytest.mark.asyncio
    async def test_propfind_response_folder_depth_0(self):
        folder = MockFolder("/test")
        result = await _propfind_response(folder, 0, ("displayname",), "/webdav")

        assert len(result) == 1  # Only the folder itself

    @pytest.mark.asyncio
    async def test_propfind_response_folder_depth_1(self):
        members = {
            "file1.txt": MockResource("/test/file1.txt"),
        }
        folder = MockFolder("/test", members)

        result = await _propfind_response(folder, 1, ("displayname",), "/webdav")

        assert len(result) == 2  # Folder + 1 member

    @pytest.mark.asyncio
    async def test_propfind(self):
        resource = MockResource("/test.txt")
        folder = MockFolder("/test")

        result = await propfind((resource, folder), 0, ("displayname",), "/webdav")

        assert isinstance(result, str)
        assert "<?xml" in result or "<D:multistatus" in result
        assert "DAV:" in result

    @pytest.mark.asyncio
    async def test_propfind_empty_members(self):
        result = await propfind((), 0, ("displayname",), "/webdav")

        assert isinstance(result, str)
        assert "multistatus" in result
