import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import List
from github import Github
from github.Repository import Repository
from github.ContentFile import ContentFile

from tgfs.config import GithubRepoConfig
from tgfs.core.model import TGFSDirectory, TGFSFileRef, TGFSMetadata
from tgfs.core.repository.impl.metadata.github_repo import GithubRepoMetadataRepository
from tgfs.core.repository.impl.metadata.github_repo.gh_directory import (
    GithubConfig,
    GithubDirectory,
)


# Global fixtures for all test classes
@pytest.fixture
def mock_github_config():
    """Create a mock GitHub configuration"""
    return GithubRepoConfig(
        access_token="test_token", repo="owner/test-repo", commit="main"
    )


@pytest.fixture
def mock_github():
    """Mock Github client"""
    github = Mock(spec=Github)
    return github


@pytest.fixture
def mock_repo():
    """Mock GitHub repository"""
    repo = Mock(spec=Repository)
    repo.name = "test-repo"
    repo.full_name = "owner/test-repo"
    return repo


@pytest.fixture
def mock_ghc(mock_github, mock_repo):
    """Mock GithubConfig"""
    return GithubConfig(
        gh=mock_github, repo_name="owner/test-repo", repo=mock_repo, commit="main"
    )


@pytest.fixture
def sample_content_file():
    """Create a sample ContentFile mock"""
    content = Mock(spec=ContentFile)
    content.name = "test_file.12345"
    content.path = "test_file.12345"
    content.type = "file"
    content.sha = "abc123"
    return content


@pytest.fixture
def sample_directory_content():
    """Create a sample directory ContentFile mock"""
    content = Mock(spec=ContentFile)
    content.name = "test_dir"
    content.path = "test_dir"
    content.type = "dir"
    return content


class TestGithubRepoMetadataRepository:
    """Test the main GithubRepoMetadataRepository class"""

    @patch("tgfs.core.repository.impl.metadata.github_repo.Github")
    def test_init_with_config(self, mock_github_class, mock_github_config):
        """Test repository initialization with GitHub config"""
        mock_github_instance = Mock(spec=Github)
        mock_repo = Mock(spec=Repository)
        mock_github_instance.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github_instance

        repository = GithubRepoMetadataRepository(mock_github_config)

        mock_github_class.assert_called_once_with("test_token")
        mock_github_instance.get_repo.assert_called_once_with("owner/test-repo")
        assert repository._ghc.repo_name == "owner/test-repo"
        assert repository._ghc.commit == "main"
        assert repository._ghc.repo == mock_repo
        assert repository._ghc.gh == mock_github_instance

    @patch("tgfs.core.repository.impl.metadata.github_repo.Github")
    @pytest.mark.asyncio
    async def test_get_metadata(self, mock_github_class, mock_github_config):
        """Test getting metadata structure"""
        mock_github_instance = Mock(spec=Github)
        mock_repo = Mock(spec=Repository)
        mock_github_instance.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github_instance

        # Mock the repo contents
        mock_repo.get_contents.return_value = []

        repository = GithubRepoMetadataRepository(mock_github_config)

        # Test get method
        result = await repository.get()

        # Should return TGFSMetadata with GithubDirectory
        assert isinstance(result, TGFSMetadata)
        assert isinstance(result.dir, GithubDirectory)
        assert result.dir.name == "root"
        assert result.dir.parent is None

    @patch("tgfs.core.repository.impl.metadata.github_repo.Github")
    def test_build_directory_structure_with_files_and_dirs(
        self, mock_github_class, mock_github_config
    ):
        """Test building directory structure with files and directories"""
        mock_github_instance = Mock(spec=Github)
        mock_repo = Mock(spec=Repository)
        mock_github_instance.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github_instance

        # Mock content structure: root -> [file1.123, subdir] -> [file2.456]
        file1 = Mock(spec=ContentFile)
        file1.name = "document.123"
        file1.type = "file"
        file1.path = "document.123"

        subdir = Mock(spec=ContentFile)
        subdir.name = "subdir"
        subdir.type = "dir"
        subdir.path = "subdir"

        file2 = Mock(spec=ContentFile)
        file2.name = "image.456"
        file2.type = "file"
        file2.path = "subdir/image.456"

        # Set up mock returns
        mock_repo.get_contents.side_effect = [
            [file1, subdir],  # root contents
            [file2],  # subdir contents
        ]

        repository = GithubRepoMetadataRepository(mock_github_config)
        root_dir = repository._build_directory_structure()

        # Verify structure
        assert root_dir.name == "root"
        assert len(root_dir.files) == 1
        assert len(root_dir.children) == 1

        # Check root file
        assert root_dir.files[0].name == "document"
        assert root_dir.files[0].message_id == 123

        # Check subdirectory
        sub_dir = root_dir.children[0]
        assert sub_dir.name == "subdir"
        assert len(sub_dir.files) == 1
        assert sub_dir.files[0].name == "image"
        assert sub_dir.files[0].message_id == 456

    @patch("tgfs.core.repository.impl.metadata.github_repo.Github")
    def test_build_directory_structure_with_gitkeep_ignored(
        self, mock_github_class, mock_github_config
    ):
        """Test that .gitkeep files are ignored during structure building"""
        mock_github_instance = Mock(spec=Github)
        mock_repo = Mock(spec=Repository)
        mock_github_instance.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github_instance

        gitkeep_file = Mock(spec=ContentFile)
        gitkeep_file.name = ".gitkeep"
        gitkeep_file.type = "file"
        gitkeep_file.path = ".gitkeep"

        regular_file = Mock(spec=ContentFile)
        regular_file.name = "test.789"
        regular_file.type = "file"
        regular_file.path = "test.789"

        mock_repo.get_contents.return_value = [gitkeep_file, regular_file]

        repository = GithubRepoMetadataRepository(mock_github_config)
        root_dir = repository._build_directory_structure()

        # Should only have the regular file, .gitkeep should be ignored
        assert len(root_dir.files) == 1
        assert root_dir.files[0].name == "test"
        assert root_dir.files[0].message_id == 789

    @patch("tgfs.core.repository.impl.metadata.github_repo.Github")
    @patch("tgfs.core.repository.impl.metadata.github_repo.logger")
    def test_build_directory_structure_handles_invalid_filename(
        self, mock_logger, mock_github_class, mock_github_config
    ):
        """Test handling of invalid filename formats"""
        mock_github_instance = Mock(spec=Github)
        mock_repo = Mock(spec=Repository)
        mock_github_instance.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github_instance

        invalid_file = Mock(spec=ContentFile)
        invalid_file.name = "invalid_filename_no_message_id"
        invalid_file.type = "file"
        invalid_file.path = "invalid_filename_no_message_id"

        mock_repo.get_contents.return_value = [invalid_file]

        repository = GithubRepoMetadataRepository(mock_github_config)
        root_dir = repository._build_directory_structure()

        # Should have no files due to invalid format
        assert len(root_dir.files) == 0

        # Should log a warning
        mock_logger.warning.assert_called_once()
        warning_call = mock_logger.warning.call_args[0][0]
        assert "Invalid name format" in warning_call
        assert "invalid_filename_no_message_id" in warning_call

    @patch("tgfs.core.repository.impl.metadata.github_repo.Github")
    @patch("tgfs.core.repository.impl.metadata.github_repo.logger")
    def test_build_directory_structure_handles_repo_errors(
        self, mock_logger, mock_github_class, mock_github_config
    ):
        """Test handling of repository access errors"""
        mock_github_instance = Mock(spec=Github)
        mock_repo = Mock(spec=Repository)
        mock_github_instance.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github_instance

        # Make get_contents raise an exception
        mock_repo.get_contents.side_effect = Exception("API rate limit exceeded")

        repository = GithubRepoMetadataRepository(mock_github_config)
        root_dir = repository._build_directory_structure()

        # Should return empty root directory
        assert root_dir.name == "root"
        assert len(root_dir.files) == 0
        assert len(root_dir.children) == 0

        # Should log error
        mock_logger.error.assert_called_once()

    @patch("tgfs.core.repository.impl.metadata.github_repo.Github")
    @patch("tgfs.core.repository.impl.metadata.github_repo.logger")
    def test_build_directory_structure_handles_subdirectory_errors(
        self, mock_logger, mock_github_class, mock_github_config
    ):
        """Test handling of subdirectory access errors"""
        mock_github_instance = Mock(spec=Github)
        mock_repo = Mock(spec=Repository)
        mock_github_instance.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github_instance

        subdir = Mock(spec=ContentFile)
        subdir.name = "protected_dir"
        subdir.type = "dir"
        subdir.path = "protected_dir"

        # Root contents succeed, subdirectory access fails
        mock_repo.get_contents.side_effect = [
            [subdir],  # root contents
            Exception("Access denied"),  # subdirectory contents
        ]

        repository = GithubRepoMetadataRepository(mock_github_config)
        root_dir = repository._build_directory_structure()

        # Should have the directory but it will be empty
        assert len(root_dir.children) == 1
        assert root_dir.children[0].name == "protected_dir"
        assert len(root_dir.children[0].files) == 0

        # Should log warning
        mock_logger.warning.assert_called_once()
        warning_call = mock_logger.warning.call_args[0][0]
        assert "Failed to construct directory protected_dir" in warning_call

    @pytest.mark.asyncio
    async def test_push_method(self, mock_github_config):
        """Test push method (currently no-op)"""
        with patch("tgfs.core.repository.impl.metadata.github_repo.Github"):
            repository = GithubRepoMetadataRepository(mock_github_config)
            # Should not raise any exception
            await repository.push()


class TestGithubDirectory:
    """Test the GithubDirectory class functionality"""

    def test_join_path_method(self):
        """Test path joining utility method"""
        # Test normal case
        result = GithubDirectory.join_path("folder1", "folder2", "file.txt")
        assert result == "folder1/folder2/file.txt"

        # Test with leading/trailing slashes
        result = GithubDirectory.join_path("/folder1/", "/folder2/", "/file.txt/")
        assert result == "folder1/folder2/file.txt"

        # Test with empty parts
        result = GithubDirectory.join_path("folder1", "", "folder2", "file.txt")
        assert result == "folder1/folder2/file.txt"

        # Test single path
        result = GithubDirectory.join_path("single")
        assert result == "single"

        # Test empty
        result = GithubDirectory.join_path()
        assert result == ""

    def test_github_path_property(self, mock_ghc):
        """Test GitHub path property calculation"""
        # Root directory
        root_dir = GithubDirectory(mock_ghc, "root", None)
        assert root_dir._github_path == ""

        # First level subdirectory
        sub_dir = GithubDirectory(mock_ghc, "subfolder", root_dir)
        assert sub_dir._github_path == "subfolder"

        # Nested subdirectory
        nested_dir = GithubDirectory(mock_ghc, "nested", sub_dir)
        assert nested_dir._github_path == "subfolder/nested"

    def test_init_with_defaults(self, mock_ghc):
        """Test GithubDirectory initialization with default values"""
        directory = GithubDirectory(mock_ghc, "test", None)

        assert directory.name == "test"
        assert directory.parent is None
        assert directory.children == []
        assert directory.files == []
        assert directory._ghc == mock_ghc

    def test_init_with_explicit_values(self, mock_ghc):
        """Test GithubDirectory initialization with explicit values"""
        children: List[TGFSDirectory] = [Mock()]
        files: List[TGFSFileRef] = [Mock()]
        parent = Mock()

        directory = GithubDirectory(mock_ghc, "test", parent, children, files)

        assert directory.name == "test"
        assert directory.parent == parent
        assert directory.children == children
        assert directory.files == files

    def test_create_dir_skip_github_ops(self, mock_ghc):
        """Test creating directory without GitHub operations"""
        parent_dir = GithubDirectory(mock_ghc, "parent", None)

        child_dir = parent_dir.create_dir_skip_github_ops("child")

        assert isinstance(child_dir, GithubDirectory)
        assert child_dir.name == "child"
        assert child_dir.parent == parent_dir
        assert child_dir in parent_dir.children
        assert child_dir._ghc == mock_ghc

    def test_create_dir_with_github_ops_success(self, mock_ghc):
        """Test creating directory with successful GitHub operations"""
        mock_ghc.repo.create_file.return_value = Mock()

        parent_dir = GithubDirectory(mock_ghc, "parent", None)
        child_dir = parent_dir.create_dir("child")

        # Verify GitHub API call - parent dir has None parent so path is just "child/.gitkeep"
        mock_ghc.repo.create_file.assert_called_once_with(
            path="child/.gitkeep",
            message="Create directory child",
            content="",
            branch="main",
        )

        # Verify directory structure
        assert isinstance(child_dir, GithubDirectory)
        assert child_dir.name == "child"
        assert child_dir.parent == parent_dir
        assert child_dir in parent_dir.children

    def test_create_dir_with_github_ops_failure(self, mock_ghc):
        """Test creating directory with GitHub operation failure"""
        mock_ghc.repo.create_file.side_effect = Exception("GitHub API error")

        parent_dir = GithubDirectory(mock_ghc, "parent", None)

        with pytest.raises(Exception, match="GitHub API error"):
            parent_dir.create_dir("child")

        # Verify no directory was added to parent
        assert len(parent_dir.children) == 0

    def test_create_file_ref_success(self, mock_ghc):
        """Test creating file reference with successful GitHub operations"""
        mock_ghc.repo.create_file.return_value = Mock()

        directory = GithubDirectory(mock_ghc, "testdir", None)
        file_ref = directory.create_file_ref("testfile", 12345)

        # Verify GitHub API call - directory has None parent so path is just the filename
        mock_ghc.repo.create_file.assert_called_once_with(
            path="testfile.12345",
            message="Create file reference for testfile",
            content="",
            branch="main",
        )

        # Verify file reference
        assert isinstance(file_ref, TGFSFileRef)
        assert file_ref.name == "testfile"
        assert file_ref.message_id == 12345
        assert file_ref in directory.files

    def test_create_file_ref_failure(self, mock_ghc):
        """Test creating file reference with GitHub operation failure"""
        mock_ghc.repo.create_file.side_effect = Exception("GitHub API error")

        directory = GithubDirectory(mock_ghc, "testdir", None)

        with pytest.raises(Exception, match="GitHub API error"):
            directory.create_file_ref("testfile", 12345)

        # Verify no file was added
        assert len(directory.files) == 0

    def test_delete_file_ref_success(self, mock_ghc):
        """Test deleting file reference with successful GitHub operations"""
        mock_content = Mock()
        mock_content.sha = "abc123"
        mock_ghc.repo.get_contents.return_value = mock_content
        mock_ghc.repo.delete_file.return_value = Mock()

        directory = GithubDirectory(mock_ghc, "testdir", None)

        # Create file ref using parent class method (which creates it properly)
        from tgfs.core.model import TGFSFileRef

        file_ref = TGFSFileRef(message_id=12345, name="testfile", location=directory)
        directory.files.append(file_ref)

        directory.delete_file_ref(file_ref)

        # Verify GitHub API calls - directory has None parent so paths are just the filenames
        mock_ghc.repo.get_contents.assert_called_once_with("testfile.12345", ref="main")
        mock_ghc.repo.delete_file.assert_called_once_with(
            path="testfile.12345",
            message="Delete file reference for testfile",
            sha="abc123",
            branch="main",
        )

        # Verify file was removed
        assert file_ref not in directory.files

    def test_delete_file_ref_with_list_content(self, mock_ghc):
        """Test deleting file reference when get_contents returns a list"""
        mock_content = Mock()
        mock_content.sha = "abc123"
        mock_ghc.repo.get_contents.return_value = [
            mock_content
        ]  # List instead of single item
        mock_ghc.repo.delete_file.return_value = Mock()

        directory = GithubDirectory(mock_ghc, "testdir", None)
        file_ref = TGFSFileRef(message_id=12345, name="testfile", location=directory)
        directory.files.append(file_ref)

        directory.delete_file_ref(file_ref)

        # Should use first item from the list - directory has None parent
        mock_ghc.repo.delete_file.assert_called_once_with(
            path="testfile.12345",
            message="Delete file reference for testfile",
            sha="abc123",
            branch="main",
        )

    @patch("tgfs.core.repository.impl.metadata.github_repo.gh_directory.logger")
    def test_delete_file_ref_failure(self, mock_logger, mock_ghc):
        """Test deleting file reference with GitHub operation failure"""
        mock_ghc.repo.get_contents.side_effect = Exception("File not found")

        directory = GithubDirectory(mock_ghc, "testdir", None)
        file_ref = TGFSFileRef(message_id=12345, name="testfile", location=directory)
        directory.files.append(file_ref)

        directory.delete_file_ref(file_ref)

        # Should log error but continue
        mock_logger.error.assert_called_once()
        error_call = mock_logger.error.call_args[0][0]
        assert "Failed to delete file reference testfile" in error_call

        # File should still be removed from local structure
        assert file_ref not in directory.files

    def test_delete_directory(self, mock_ghc):
        """Test deleting directory"""
        mock_content1 = Mock()
        mock_content1.path = "testdir/file1.txt"
        mock_content1.sha = "sha1"

        mock_content2 = Mock()
        mock_content2.path = "testdir/file2.txt"
        mock_content2.sha = "sha2"

        mock_ghc.repo.get_contents.return_value = [mock_content1, mock_content2]
        mock_ghc.repo.delete_file.return_value = Mock()

        parent = Mock()
        parent.children = []

        directory = GithubDirectory(mock_ghc, "testdir", parent)
        parent.children.append(directory)

        directory.delete()

        # Verify GitHub API calls
        mock_ghc.repo.get_contents.assert_called_once_with("testdir", ref="main")
        assert mock_ghc.repo.delete_file.call_count == 2

        # Verify directory was removed from parent
        assert directory not in parent.children

    @patch("tgfs.core.repository.impl.metadata.github_repo.gh_directory.logger")
    def test_delete_directory_handles_errors(self, mock_logger, mock_ghc):
        """Test deleting directory with error handling"""
        mock_ghc.repo.get_contents.side_effect = Exception("Access denied")

        parent = Mock()
        parent.children = []

        directory = GithubDirectory(mock_ghc, "testdir", parent)
        parent.children.append(directory)

        directory.delete()

        # Should log error
        mock_logger.error.assert_called_once()
        error_call = mock_logger.error.call_args[0][0]
        assert "Failed to delete directory testdir" in error_call

        # Directory should still be removed from parent
        assert directory not in parent.children


class TestGithubConfig:
    """Test the GithubConfig dataclass"""

    def test_github_config_creation(self):
        """Test creating GithubConfig"""
        gh = Mock(spec=Github)
        repo = Mock(spec=Repository)

        config = GithubConfig(gh=gh, repo_name="owner/repo", repo=repo, commit="main")

        assert config.gh == gh
        assert config.repo_name == "owner/repo"
        assert config.repo == repo
        assert config.commit == "main"


class TestIntegrationScenarios:
    """Integration tests for complete workflows"""

    @patch("tgfs.core.repository.impl.metadata.github_repo.Github")
    @pytest.mark.asyncio
    async def test_complete_workflow_file_operations(
        self, mock_github_class, mock_github_config
    ):
        """Test complete workflow of creating and managing files"""
        mock_github_instance = Mock(spec=Github)
        mock_repo = Mock(spec=Repository)
        mock_github_instance.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github_instance

        # Mock initial empty repository
        mock_repo.get_contents.return_value = []

        repository = GithubRepoMetadataRepository(mock_github_config)
        metadata = await repository.get()
        root_dir = metadata.dir

        # Create a subdirectory
        mock_repo.create_file.return_value = Mock()
        sub_dir = root_dir.create_dir("documents", None)

        # Create file references
        file_ref1 = sub_dir.create_file_ref("report", 11111)
        file_ref2 = sub_dir.create_file_ref("presentation", 22222)

        # Verify structure
        assert len(root_dir.children) == 1
        assert len(sub_dir.files) == 2
        assert file_ref1.name == "report"
        assert file_ref2.name == "presentation"

        # Delete a file
        mock_content = Mock()
        mock_content.sha = "abc123"
        mock_repo.get_contents.return_value = mock_content
        sub_dir.delete_file_ref(file_ref1)

        assert len(sub_dir.files) == 1
        assert file_ref1 not in sub_dir.files

    @patch("tgfs.core.repository.impl.metadata.github_repo.Github")
    def test_complex_directory_structure_building(
        self, mock_github_class, mock_github_config
    ):
        """Test building complex nested directory structures"""
        mock_github_instance = Mock(spec=Github)
        mock_repo = Mock(spec=Repository)
        mock_github_instance.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github_instance

        # Create complex structure: root/docs/2023/reports/ with files
        docs_dir = Mock(spec=ContentFile)
        docs_dir.name = "docs"
        docs_dir.type = "dir"
        docs_dir.path = "docs"

        year_dir = Mock(spec=ContentFile)
        year_dir.name = "2023"
        year_dir.type = "dir"
        year_dir.path = "docs/2023"

        reports_dir = Mock(spec=ContentFile)
        reports_dir.name = "reports"
        reports_dir.type = "dir"
        reports_dir.path = "docs/2023/reports"

        file1 = Mock(spec=ContentFile)
        file1.name = "q1_report.111"
        file1.type = "file"
        file1.path = "docs/2023/reports/q1_report.111"

        file2 = Mock(spec=ContentFile)
        file2.name = "q2_report.222"
        file2.type = "file"
        file2.path = "docs/2023/reports/q2_report.222"

        # Set up mock returns
        mock_repo.get_contents.side_effect = [
            [docs_dir],  # root
            [year_dir],  # docs/
            [reports_dir],  # docs/2023/
            [file1, file2],  # docs/2023/reports/
        ]

        repository = GithubRepoMetadataRepository(mock_github_config)
        root_dir = repository._build_directory_structure()

        # Navigate and verify structure
        assert len(root_dir.children) == 1
        docs = root_dir.children[0]
        assert docs.name == "docs"

        assert len(docs.children) == 1
        year_2023 = docs.children[0]
        assert year_2023.name == "2023"

        assert len(year_2023.children) == 1
        reports = year_2023.children[0]
        assert reports.name == "reports"

        assert len(reports.files) == 2
        file_names = {f.name for f in reports.files}
        assert file_names == {"q1_report", "q2_report"}

        message_ids = {f.message_id for f in reports.files}
        assert message_ids == {111, 222}


class TestErrorHandling:
    """Test error handling scenarios"""

    @patch("tgfs.core.repository.impl.metadata.github_repo.Github")
    def test_invalid_github_token(self, mock_github_class, mock_github_config):
        """Test handling of invalid GitHub token"""
        mock_github_class.side_effect = Exception("Bad credentials")

        with pytest.raises(Exception, match="Bad credentials"):
            GithubRepoMetadataRepository(mock_github_config)

    @patch("tgfs.core.repository.impl.metadata.github_repo.Github")
    def test_invalid_repository(self, mock_github_class, mock_github_config):
        """Test handling of invalid repository"""
        mock_github_instance = Mock(spec=Github)
        mock_github_instance.get_repo.side_effect = Exception("Repository not found")
        mock_github_class.return_value = mock_github_instance

        with pytest.raises(Exception, match="Repository not found"):
            GithubRepoMetadataRepository(mock_github_config)

    def test_file_ref_with_non_numeric_message_id(self, mock_ghc):
        """Test error handling for non-numeric message IDs in filenames"""
        mock_content = Mock(spec=ContentFile)
        mock_content.name = "test.abc"  # Non-numeric message ID
        mock_content.type = "file"
        mock_content.path = "test.abc"

        mock_ghc.repo.get_contents.return_value = [mock_content]

        with patch("tgfs.core.repository.impl.metadata.github_repo.Github"):
            repository = GithubRepoMetadataRepository(
                GithubRepoConfig(access_token="test", repo="test/repo", commit="main")
            )
            repository._ghc = mock_ghc

            with patch(
                "tgfs.core.repository.impl.metadata.github_repo.logger"
            ) as mock_logger:
                root_dir = repository._build_directory_structure()

                # Should have no files due to invalid format
                assert len(root_dir.files) == 0

                # Should log warning about invalid format
                mock_logger.warning.assert_called_once()


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_empty_repository(self, mock_ghc):
        """Test handling of completely empty repository"""
        mock_ghc.repo.get_contents.return_value = []

        with patch("tgfs.core.repository.impl.metadata.github_repo.Github"):
            repository = GithubRepoMetadataRepository(
                GithubRepoConfig(access_token="test", repo="test/repo", commit="main")
            )
            repository._ghc = mock_ghc

            root_dir = repository._build_directory_structure()

            assert root_dir.name == "root"
            assert len(root_dir.files) == 0
            assert len(root_dir.children) == 0

    def test_directory_with_only_gitkeep(self, mock_ghc):
        """Test directory containing only .gitkeep files"""
        gitkeep1 = Mock(spec=ContentFile)
        gitkeep1.name = ".gitkeep"
        gitkeep1.type = "file"
        gitkeep1.path = ".gitkeep"

        gitkeep2 = Mock(spec=ContentFile)
        gitkeep2.name = ".gitkeep"
        gitkeep2.type = "file"
        gitkeep2.path = "subdir/.gitkeep"

        subdir = Mock(spec=ContentFile)
        subdir.name = "subdir"
        subdir.type = "dir"
        subdir.path = "subdir"

        mock_ghc.repo.get_contents.side_effect = [
            [gitkeep1, subdir],  # root
            [gitkeep2],  # subdir
        ]

        with patch("tgfs.core.repository.impl.metadata.github_repo.Github"):
            repository = GithubRepoMetadataRepository(
                GithubRepoConfig(access_token="test", repo="test/repo", commit="main")
            )
            repository._ghc = mock_ghc

            root_dir = repository._build_directory_structure()

            # Should have subdirectory but no files
            assert len(root_dir.files) == 0
            assert len(root_dir.children) == 1
            assert root_dir.children[0].name == "subdir"
            assert len(root_dir.children[0].files) == 0

    def test_single_content_item_not_in_list(self, mock_ghc):
        """Test handling when get_contents returns single item instead of list"""
        single_file = Mock(spec=ContentFile)
        single_file.name = "single.123"
        single_file.type = "file"
        single_file.path = "single.123"

        mock_ghc.repo.get_contents.return_value = single_file  # Single item, not list

        with patch("tgfs.core.repository.impl.metadata.github_repo.Github"):
            repository = GithubRepoMetadataRepository(
                GithubRepoConfig(access_token="test", repo="test/repo", commit="main")
            )
            repository._ghc = mock_ghc

            root_dir = repository._build_directory_structure()

            # Should handle single item correctly
            assert len(root_dir.files) == 1
            assert root_dir.files[0].name == "single"
            assert root_dir.files[0].message_id == 123
