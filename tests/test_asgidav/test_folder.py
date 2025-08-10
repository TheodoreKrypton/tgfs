import pytest
from asgidav.folder import Folder
from asgidav.member import ResourceType
from .common import MockFolder, MockResource


class TestFolder:
    def test_folder_resource_type(self):
        folder = MockFolder("/test")
        assert folder.resource_type == ResourceType.COLLECTION

    @pytest.mark.asyncio
    async def test_content_type(self):
        folder = MockFolder("/test")
        assert await folder.content_type() == "httpd/unix-directory"

    @pytest.mark.asyncio
    async def test_content_length(self):
        folder = MockFolder("/test")
        assert await folder.content_length() == 0

    @pytest.mark.asyncio
    async def test_get_properties_empty_folder(self):
        folder = MockFolder("/empty")
        properties = await folder.get_properties()
        
        assert properties["childcount"] == 0
        assert properties["displayname"] == "empty"
        assert properties["getcontenttype"] == "httpd/unix-directory"
        assert properties["resourcetype"] == "collection"

    @pytest.mark.asyncio
    async def test_get_properties_with_members(self):
        members = {
            "file1.txt": MockResource("/test/file1.txt"),
            "file2.txt": MockResource("/test/file2.txt"),
            "subfolder": MockFolder("/test/subfolder"),
        }
        folder = MockFolder("/test", members)
        properties = await folder.get_properties()
        
        assert properties["childcount"] == 3

    @pytest.mark.asyncio
    async def test_member_names(self):
        members = {
            "file1.txt": MockResource("/test/file1.txt"),
            "subfolder": MockFolder("/test/subfolder"),
        }
        folder = MockFolder("/test", members)
        
        names = await folder.member_names()
        assert set(names) == {"file1.txt", "subfolder"}

    @pytest.mark.asyncio
    async def test_member(self):
        resource = MockResource("/test/file.txt")
        members = {"file.txt": resource}
        folder = MockFolder("/test", members)
        
        found_member = await folder.member("file.txt")
        assert found_member is resource
        
        not_found = await folder.member("nonexistent.txt")
        assert not_found is None

    @pytest.mark.asyncio
    async def test_create_empty_resource(self):
        folder = MockFolder("/test")
        resource = await folder.create_empty_resource("new_file.txt")
        
        assert resource is not None
        assert resource.path == "new_file.txt"
        assert "new_file.txt" in folder._members

    @pytest.mark.asyncio
    async def test_create_folder(self):
        folder = MockFolder("/test")
        subfolder = await folder.create_folder("subfolder")
        
        assert isinstance(subfolder, Folder)
        assert subfolder.path == "/test/subfolder"
        assert "subfolder" in folder._members
