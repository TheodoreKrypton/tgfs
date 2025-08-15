import pytest
from unittest.mock import Mock

from tgfs.core.model import TGFSFileRefSerialized
from tgfs.core.model.directory import TGFSDirectory, TGFSFileRef
from tgfs.errors import (
    FileOrDirectoryAlreadyExists,
    FileOrDirectoryDoesNotExist,
    InvalidName,
)
from tgfs.utils.time import FIRST_DAY_OF_EPOCH, ts


class TestTGFSFileRef:
    def test_init(self):
        # Test creating a file reference
        parent_dir = TGFSDirectory.root_dir()
        file_ref = TGFSFileRef(message_id=123, name="test.txt", location=parent_dir)

        assert file_ref.message_id == 123
        assert file_ref.name == "test.txt"
        assert file_ref.location == parent_dir

    def test_to_dict(self):
        # Test serialization to dictionary
        parent_dir = TGFSDirectory.root_dir()
        file_ref = TGFSFileRef(message_id=456, name="document.pdf", location=parent_dir)

        result = file_ref.to_dict()
        expected = {
            "type": "FR",
            "messageId": 456,
            "name": "document.pdf",
        }

        assert result == expected

    def test_delete(self):
        # Test deleting a file reference
        parent_dir = TGFSDirectory.root_dir()
        file_ref = TGFSFileRef(message_id=123, name="test.txt", location=parent_dir)
        parent_dir.files.append(file_ref)

        file_ref.delete()

        assert file_ref not in parent_dir.files


class TestTGFSDirectory:
    def test_init_minimal(self):
        # Test creating directory with minimal parameters
        directory = TGFSDirectory(name="test_dir", parent=None)

        assert directory.name == "test_dir"
        assert directory.parent is None
        assert directory.children == []
        assert directory.files == []

    def test_init_with_parent(self):
        # Test creating directory with parent
        parent = TGFSDirectory(name="parent", parent=None)
        child = TGFSDirectory(name="child", parent=parent)

        assert child.name == "child"
        assert child.parent == parent
        assert child.children == []
        assert child.files == []

    def test_init_with_children_and_files(self):
        # Test creating directory with children and files
        parent = TGFSDirectory(name="parent", parent=None)
        child = TGFSDirectory(name="child", parent=parent)
        file_ref = TGFSFileRef(message_id=123, name="test.txt", location=parent)

        directory = TGFSDirectory(
            name="test_dir", parent=None, children=[child], files=[file_ref]
        )

        assert directory.name == "test_dir"
        assert directory.children == [child]
        assert directory.files == [file_ref]

    def test_post_init_name_validation(self):
        # Test that name validation is called during initialization
        with pytest.raises(InvalidName):
            TGFSDirectory(name="-invalid", parent=None)

        with pytest.raises(InvalidName):
            TGFSDirectory(name="invalid/name", parent=None)

    def test_created_at_timestamp_property(self):
        # Test timestamp property (always returns FIRST_DAY_OF_EPOCH)
        directory = TGFSDirectory(name="test", parent=None)

        assert directory.created_at_timestamp == ts(FIRST_DAY_OF_EPOCH)

    def test_to_dict_empty(self):
        # Test serialization of empty directory
        directory = TGFSDirectory(name="empty", parent=None)

        result = directory.to_dict()
        expected = {
            "type": "D",
            "name": "empty",
            "children": [],
            "files": [],
        }

        assert result == expected

    def test_to_dict_with_content(self):
        # Test serialization with children and files
        parent = TGFSDirectory(name="parent", parent=None)
        child = TGFSDirectory(name="child", parent=parent)
        file_ref = TGFSFileRef(message_id=123, name="test.txt", location=parent)

        parent.children.append(child)
        parent.files.append(file_ref)

        result = parent.to_dict()

        assert result["type"] == "D"
        assert result["name"] == "parent"
        assert len(result["children"]) == 1
        assert result["children"][0]["name"] == "child"
        assert len(result["files"]) == 1
        assert result["files"][0]["name"] == "test.txt"

    def test_from_dict_minimal(self):
        # Test deserialization from minimal dictionary
        directory = TGFSDirectory.from_dict(
            {
                "type": "D",
                "name": "test_dir",
                "children": [],
                "files": [],
            }
        )

        assert directory.name == "test_dir"
        assert directory.parent is None
        assert directory.children == []
        assert directory.files == []

    def test_from_dict_with_parent(self):
        # Test deserialization with parent
        parent = TGFSDirectory(name="parent", parent=None)

        directory = TGFSDirectory.from_dict(
            {
                "type": "D",
                "name": "child_dir",
                "children": [],
                "files": [],
            },
            parent,
        )

        assert directory.name == "child_dir"
        assert directory.parent == parent

    def test_from_dict_with_files(self):
        # Test deserialization with files
        directory = TGFSDirectory.from_dict(
            {
                "type": "D",
                "name": "test_dir",
                "children": [],
                "files": [
                    TGFSFileRefSerialized(type="FR", messageId=123, name="file1.txt"),
                    TGFSFileRefSerialized(type="FR", messageId=456, name="file2.pdf"),
                ],
            }
        )

        assert directory.name == "test_dir"
        assert len(directory.files) == 2
        assert directory.files[0].name == "file1.txt"
        assert directory.files[0].message_id == 123
        assert directory.files[0].location == directory
        assert directory.files[1].name == "file2.pdf"
        assert directory.files[1].message_id == 456

    def test_from_dict_with_invalid_files(self):
        # Test deserialization with invalid files (missing name or messageId)
        directory = TGFSDirectory.from_dict(
            {
                "name": "test_dir",
                "children": [],
                "files": [
                    {"messageId": 123, "name": "valid.txt"},
                    {"messageId": 456, "name": ""},  # Empty name
                    {
                        "messageId": 0,
                        "name": "no_message.txt",
                    },  # Zero message ID (falsy)
                ],
            }
        )

        # Only files with non-empty name and non-zero messageId should be included
        assert len(directory.files) == 1
        assert directory.files[0].name == "valid.txt"

    def test_from_dict_with_children(self):
        # Test deserialization with nested children
        directory = TGFSDirectory.from_dict(
            {
                "name": "root",
                "children": [
                    {
                        "name": "child1",
                        "children": [],
                        "files": [],
                    },
                    {
                        "name": "child2",
                        "children": [
                            {
                                "name": "grandchild",
                                "children": [],
                                "files": [],
                            }
                        ],
                        "files": [],
                    },
                ],
                "files": [],
            }
        )

        assert directory.name == "root"
        assert len(directory.children) == 2

        child1 = directory.children[0]
        assert child1.name == "child1"
        assert child1.parent == directory

        child2 = directory.children[1]
        assert child2.name == "child2"
        assert child2.parent == directory
        assert len(child2.children) == 1

        grandchild = child2.children[0]
        assert grandchild.name == "grandchild"
        assert grandchild.parent == child2

    def test_create_dir_new(self):
        # Test creating a new directory
        parent = TGFSDirectory(name="parent", parent=None)

        child = parent.create_dir("new_dir", None)

        assert child.name == "new_dir"
        assert child.parent == parent
        assert child in parent.children
        assert child.children == []
        assert child.files == []

    def test_create_dir_with_copy(self):
        # Test creating directory by copying another
        template = TGFSDirectory(name="template", parent=None)
        template_child = TGFSDirectory(name="template_child", parent=template)
        template_file = TGFSFileRef(
            message_id=123, name="template.txt", location=template
        )
        template.children.append(template_child)
        template.files.append(template_file)

        parent = TGFSDirectory(name="parent", parent=None)

        copy_dir = parent.create_dir("copy", template)

        assert copy_dir.name == "copy"
        assert copy_dir.parent == parent
        assert copy_dir.children == template.children
        assert copy_dir.files == template.files

    def test_create_dir_already_exists(self):
        # Test creating directory that already exists
        parent = TGFSDirectory(name="parent", parent=None)
        existing = TGFSDirectory(name="existing", parent=parent)
        parent.children.append(existing)

        with pytest.raises(FileOrDirectoryAlreadyExists):
            parent.create_dir("existing", None)

    def test_root_dir_factory(self):
        # Test creating root directory
        root = TGFSDirectory.root_dir()

        assert root.name == "root"
        assert root.parent is None
        assert root.children == []
        assert root.files == []

    def test_find_dirs_all(self):
        # Test finding all directories
        parent = TGFSDirectory(name="parent", parent=None)
        child1 = TGFSDirectory(name="child1", parent=parent)
        child2 = TGFSDirectory(name="child2", parent=parent)
        parent.children.extend([child1, child2])

        result = parent.find_dirs()

        assert len(result) == 2
        assert child1 in result
        assert child2 in result

    def test_find_dirs_by_names(self):
        # Test finding directories by specific names
        parent = TGFSDirectory(name="parent", parent=None)
        child1 = TGFSDirectory(name="target", parent=parent)
        child2 = TGFSDirectory(name="other", parent=parent)
        child3 = TGFSDirectory(name="also_target", parent=parent)
        parent.children.extend([child1, child2, child3])

        result = parent.find_dirs(["target", "also_target"])

        assert len(result) == 2
        assert child1 in result
        assert child3 in result
        assert child2 not in result

    def test_find_dirs_empty_result(self):
        # Test finding directories with no matches
        parent = TGFSDirectory(name="parent", parent=None)
        child = TGFSDirectory(name="child", parent=parent)
        parent.children.append(child)

        result = parent.find_dirs(["nonexistent"])

        assert result == []

    def test_find_dir_exists(self):
        # Test finding single directory that exists
        parent = TGFSDirectory(name="parent", parent=None)
        target = TGFSDirectory(name="target", parent=parent)
        parent.children.append(target)

        result = parent.find_dir("target")

        assert result == target

    def test_find_dir_not_exists(self):
        # Test finding single directory that doesn't exist
        parent = TGFSDirectory(name="parent", parent=None)

        with pytest.raises(FileOrDirectoryDoesNotExist):
            parent.find_dir("nonexistent")

    def test_find_files_all(self):
        # Test finding all files
        parent = TGFSDirectory(name="parent", parent=None)
        file1 = TGFSFileRef(message_id=123, name="file1.txt", location=parent)
        file2 = TGFSFileRef(message_id=456, name="file2.pdf", location=parent)
        parent.files.extend([file1, file2])

        result = parent.find_files()

        assert len(result) == 2
        assert file1 in result
        assert file2 in result

    def test_find_files_by_names(self):
        # Test finding files by specific names
        parent = TGFSDirectory(name="parent", parent=None)
        file1 = TGFSFileRef(message_id=123, name="target.txt", location=parent)
        file2 = TGFSFileRef(message_id=456, name="other.pdf", location=parent)
        file3 = TGFSFileRef(message_id=789, name="also_target.doc", location=parent)
        parent.files.extend([file1, file2, file3])

        result = parent.find_files(["target.txt", "also_target.doc"])

        assert len(result) == 2
        assert file1 in result
        assert file3 in result
        assert file2 not in result

    def test_find_files_empty_result(self):
        # Test finding files with no matches
        parent = TGFSDirectory(name="parent", parent=None)
        file_ref = TGFSFileRef(message_id=123, name="existing.txt", location=parent)
        parent.files.append(file_ref)

        result = parent.find_files(["nonexistent.txt"])

        assert result == []

    def test_find_file_exists(self):
        # Test finding single file that exists
        parent = TGFSDirectory(name="parent", parent=None)
        target = TGFSFileRef(message_id=123, name="target.txt", location=parent)
        parent.files.append(target)

        result = parent.find_file("target.txt")

        assert result == target

    def test_find_file_not_exists(self):
        # Test finding single file that doesn't exist
        parent = TGFSDirectory(name="parent", parent=None)

        with pytest.raises(FileOrDirectoryDoesNotExist):
            parent.find_file("nonexistent.txt")

    def test_create_file_ref_new(self):
        # Test creating new file reference
        parent = TGFSDirectory(name="parent", parent=None)

        file_ref = parent.create_file_ref("new_file.txt", 123)

        assert file_ref.name == "new_file.txt"
        assert file_ref.message_id == 123
        assert file_ref.location == parent
        assert file_ref in parent.files

    def test_create_file_ref_already_exists(self):
        # Test creating file reference that already exists
        parent = TGFSDirectory(name="parent", parent=None)
        existing = TGFSFileRef(message_id=123, name="existing.txt", location=parent)
        parent.files.append(existing)

        with pytest.raises(FileOrDirectoryAlreadyExists):
            parent.create_file_ref("existing.txt", 456)

    def test_delete_file_ref(self):
        # Test deleting file reference
        parent = TGFSDirectory(name="parent", parent=None)
        file_ref = TGFSFileRef(message_id=123, name="test.txt", location=parent)
        parent.files.append(file_ref)

        parent.delete_file_ref(file_ref)

        assert file_ref not in parent.files

    def test_delete_with_parent(self):
        # Test deleting directory with parent
        parent = TGFSDirectory(name="parent", parent=None)
        child = TGFSDirectory(name="child", parent=parent)
        parent.children.append(child)

        child.delete()

        assert child not in parent.children

    def test_delete_root_directory(self):
        # Test deleting root directory (clears contents)
        root = TGFSDirectory.root_dir()
        child = TGFSDirectory(name="child", parent=root)
        file_ref = TGFSFileRef(message_id=123, name="test.txt", location=root)
        root.children.append(child)
        root.files.append(file_ref)

        root.delete()

        assert root.children == []
        assert root.files == []

    def test_absolute_path_root(self):
        # Test absolute path for root directory
        root = TGFSDirectory.root_dir()
        root.parent = None  # Explicit None for root

        assert root.absolute_path == ""

    def test_absolute_path_single_level(self):
        # Test absolute path for single level directory
        root = TGFSDirectory.root_dir()
        child = TGFSDirectory(name="folder", parent=root)

        assert child.absolute_path == "/folder"

    def test_absolute_path_nested(self):
        # Test absolute path for nested directories
        root = TGFSDirectory.root_dir()
        level1 = TGFSDirectory(name="level1", parent=root)
        level2 = TGFSDirectory(name="level2", parent=level1)
        level3 = TGFSDirectory(name="level3", parent=level2)

        assert level1.absolute_path == "/level1"
        assert level2.absolute_path == "/level1/level2"
        assert level3.absolute_path == "/level1/level2/level3"

    def test_absolute_path_empty_name(self):
        # Test absolute path with empty directory name - this should raise InvalidName
        root = TGFSDirectory.root_dir()

        # Empty names are not allowed, so this should raise an exception
        with pytest.raises(IndexError):
            TGFSDirectory(name="", parent=root)

    def test_absolute_path_complex_hierarchy(self):
        # Test absolute path in complex directory hierarchy
        root = TGFSDirectory.root_dir()
        documents = TGFSDirectory(name="Documents", parent=root)
        projects = TGFSDirectory(name="Projects", parent=documents)
        myproject = TGFSDirectory(name="MyProject", parent=projects)
        src = TGFSDirectory(name="src", parent=myproject)

        assert documents.absolute_path == "/Documents"
        assert projects.absolute_path == "/Documents/Projects"
        assert myproject.absolute_path == "/Documents/Projects/MyProject"
        assert src.absolute_path == "/Documents/Projects/MyProject/src"
