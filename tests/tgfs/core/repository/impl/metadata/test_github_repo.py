import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import Mock, patch

import pytest
from github import Github, GithubException
from github.ContentFile import ContentFile
from github.Repository import Repository

from tgfs.config import GithubRepoConfig
from tgfs.core.model import TGFSDirectory, TGFSFileRef, TGFSMetadata
from tgfs.core.repository.impl.metadata.github_repo import GithubRepoMetadataRepository
from tgfs.core.repository.impl.metadata.github_repo.gh_directory import (
    GithubConfig,
    GithubDirectory,
)
from tgfs.errors import TechnicalError

# --- Deterministic fakes for the Git Trees API -------------------------------
#
# The metadata repository is very wide (~100k entries), so the loader must read
# it through the Git Trees API rather than the contents API, and it must take
# the largest subtree GitHub is willing to return in one request: a per
# directory walk costs one request per directory and gets rate limited long
# before the tree is loaded.
#
# The fake below answers exactly like the real endpoint: ``recursive=True``
# flattens every descendant into slash separated paths, ``recursive=False``
# returns only the immediate children, and either answer can be marked
# truncated independently.


class FakeTreeElement:
    """Stand-in for github.GitTreeElement.GitTreeElement"""

    def __init__(self, path: str, type: str, sha: str):
        self.path = path
        self.type = type
        self.sha = sha


class FakeGitTree:
    """Stand-in for github.GitTree.GitTree"""

    def __init__(
        self, sha: str, elements: List[FakeTreeElement], truncated: bool = False
    ):
        self.sha = sha
        self.tree = list(elements)
        self.truncated = truncated


class Submodule:
    """Marker for a gitlink ('commit') entry in a fake structure"""


SUBMODULE = Submodule()


def tree_sha(path: str) -> str:
    return f"tree:{path}"


def blob_sha(path: str) -> str:
    return f"blob:{path}"


class FakeTreeApi:
    """Callable replacement for Repository.get_git_tree backed by a nested structure.

    A dict value is a subtree, ``SUBMODULE`` is a gitlink, any other value
    (``None``) is a blob. SHAs are derived from the absolute path so assertions
    can name them, while ``element.path`` is relative to the fetched tree, as
    GitHub returns it.

    ``recursive`` defaults to None so that tests can assert the loader passes it
    explicitly rather than relying on a default.
    """

    def __init__(self, structure: Dict[str, Any], root_sha: str):
        self.root_sha = root_sha
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.paths: Dict[str, str] = {}
        self.calls: List[tuple[str, Optional[bool]]] = []
        self.truncated_recursive: set[str] = set()
        self.truncated_nonrecursive: set[str] = set()
        self.errors: Dict[str, Exception] = {}

        self._index(root_sha, "", structure)

    def _index(self, sha: str, path: str, node: Dict[str, Any]) -> None:
        self.nodes[sha] = node
        self.paths[sha] = path
        for name, child in node.items():
            if isinstance(child, dict):
                child_path = f"{path}/{name}" if path else name
                self._index(tree_sha(child_path), child_path, child)

    def _elements(self, sha: str, recursive: bool) -> List[FakeTreeElement]:
        elements: List[FakeTreeElement] = []

        def walk(node: Dict[str, Any], abs_prefix: str, rel_prefix: str) -> None:
            for name, child in node.items():
                abs_path = f"{abs_prefix}/{name}" if abs_prefix else name
                rel_path = f"{rel_prefix}/{name}" if rel_prefix else name
                if isinstance(child, dict):
                    elements.append(
                        FakeTreeElement(rel_path, "tree", tree_sha(abs_path))
                    )
                    if recursive:
                        walk(child, abs_path, rel_path)
                elif isinstance(child, Submodule):
                    elements.append(
                        FakeTreeElement(rel_path, "commit", f"commit:{abs_path}")
                    )
                else:
                    elements.append(
                        FakeTreeElement(rel_path, "blob", blob_sha(abs_path))
                    )

        walk(self.nodes[sha], self.paths[sha], "")
        return elements

    def __call__(self, sha: str, recursive: Optional[bool] = None) -> FakeGitTree:
        self.calls.append((sha, recursive))

        if sha in self.errors:
            raise self.errors[sha]
        if sha not in self.nodes:
            raise GithubException(404, data={"message": "Not Found"})

        truncated = sha in (
            self.truncated_recursive if recursive else self.truncated_nonrecursive
        )
        return FakeGitTree(sha, self._elements(sha, bool(recursive)), truncated)

    # -- test controls --------------------------------------------------------

    def truncate_recursive(self, sha: str) -> None:
        """GitHub answers the recursive listing of this tree with truncated=True"""
        self.truncated_recursive.add(sha)

    def truncate_completely(self, sha: str) -> None:
        """Even the immediate children of this tree do not fit in one response"""
        self.truncated_recursive.add(sha)
        self.truncated_nonrecursive.add(sha)

    def fail(self, sha: str, ex: Exception) -> None:
        self.errors[sha] = ex

    def forget(self, sha: str) -> None:
        """Make this tree unreachable, as an unreadable subtree would be"""
        del self.nodes[sha]

    # -- assertions helpers ---------------------------------------------------

    @property
    def recursive_calls(self) -> List[str]:
        return [sha for sha, recursive in self.calls if recursive]

    @property
    def nonrecursive_calls(self) -> List[str]:
        return [sha for sha, recursive in self.calls if not recursive]


def root_tree_sha(ref: str) -> str:
    """The tree SHA a ref resolves to. Deliberately different from the ref itself."""
    return f"tree-of:{ref}"


class FakeGitTreeRef:
    """Stand-in for the GitTree carried by a GitCommit (only ``sha`` is populated)"""

    def __init__(self, sha: str):
        self.sha = sha


class FakeGitCommit:
    """Stand-in for github.GitCommit.GitCommit"""

    def __init__(self, tree_sha: str):
        self.tree = FakeGitTreeRef(tree_sha)


class FakeCommit:
    """Stand-in for github.Commit.Commit, as returned by Branch.commit"""

    def __init__(self, sha: str, tree_sha: str):
        self.sha = sha
        self.commit = FakeGitCommit(tree_sha)


class FakeBranch:
    """Stand-in for github.Branch.Branch"""

    def __init__(self, name: str, tree_sha: str):
        self.name = name
        self.commit = FakeCommit(f"commit-of:{name}", tree_sha)


class FakeBranchApi:
    """Callable replacement for Repository.get_branch backed by a ref -> tree sha map.

    Unlike ``get_git_tree``, the branches endpoint accepts refs containing a
    slash, so this is the only way a config like ``metadata/main`` can be
    turned into something the Git Trees API can be called with.
    """

    def __init__(self, refs: Dict[str, str]):
        self.refs = refs
        self.calls: List[str] = []

    def __call__(self, branch: str) -> FakeBranch:
        self.calls.append(branch)
        if branch not in self.refs:
            raise GithubException(404, data={"message": "Branch not found"})
        return FakeBranch(branch, self.refs[branch])


def make_tree_api(root_ref: str, structure: Dict[str, Any]) -> FakeTreeApi:
    """A FakeTreeApi whose root tree is keyed by the SHA ``root_ref`` resolves to.

    The root is never keyed by the ref itself: the loader has to resolve the
    ref before it may call the trees endpoint.
    """
    return FakeTreeApi(structure, root_sha=root_tree_sha(root_ref))


def install_fake_github(
    mock_repo: Any, structure: Dict[str, Any], ref: str = "main"
) -> tuple[FakeTreeApi, FakeBranchApi]:
    """Wire both halves of the API the loader needs: ref resolution + tree walking"""
    tree_api = make_tree_api(ref, structure)
    branch_api = FakeBranchApi({ref: tree_api.root_sha})

    mock_repo.get_branch.side_effect = branch_api
    mock_repo.get_git_tree.side_effect = tree_api

    return tree_api, branch_api


def build_repository(
    mock_github_class: Any, config: GithubRepoConfig, structure: Dict[str, Any]
) -> tuple[GithubRepoMetadataRepository, Any, FakeTreeApi, FakeBranchApi]:
    """A repository whose configured ref resolves to the root of ``structure``"""
    mock_github_instance = Mock(spec=Github)
    mock_repo = Mock(spec=Repository)
    mock_github_instance.get_repo.return_value = mock_repo
    mock_github_class.return_value = mock_github_instance

    tree_api, branch_api = install_fake_github(mock_repo, structure, ref=config.commit)

    return GithubRepoMetadataRepository(config), mock_repo, tree_api, branch_api


def cache_envelope(
    metadata: TGFSMetadata,
    *,
    repo: str,
    configured_ref: str,
    resolved_tree_sha: str,
) -> dict:
    return {
        "cache_version": 1,
        "repo": repo,
        "configured_ref": configured_ref,
        "resolved_tree_sha": resolved_tree_sha,
        "written_at": "2026-09-04T00:00:00Z",
        "metadata": metadata.to_dict(),
    }


def write_cache(
    path: Path,
    metadata: TGFSMetadata,
    *,
    repo: str,
    configured_ref: str,
    resolved_tree_sha: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            cache_envelope(
                metadata,
                repo=repo,
                configured_ref=configured_ref,
                resolved_tree_sha=resolved_tree_sha,
            )
        )
    )


def conflict_422() -> GithubException:
    """The exception PyGithub raises when the path already exists."""
    return GithubException(
        422, data={"message": 'Invalid request.\n\n"sha" wasn\'t supplied.'}
    )


def existing_content(path: str) -> Mock:
    content = Mock(spec=ContentFile)
    content.path = path
    content.name = path.rsplit("/", 1)[-1]
    content.type = "file"
    content.sha = "existing-sha"
    return content


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
        install_fake_github(mock_repo, {})

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

        # Mock tree structure: root -> [document.123, subdir] -> [image.456]
        install_fake_github(
            mock_repo,
            {
                "document.123": None,
                "subdir": {"image.456": None},
            },
        )

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

        install_fake_github(mock_repo, {".gitkeep": None, "test.789": None})

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

        install_fake_github(mock_repo, {"invalid_filename_no_message_id": None})

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
    def test_build_directory_structure_raises_on_repo_errors(
        self, mock_logger, mock_github_class, mock_github_config
    ):
        """Repository access errors must surface, not yield an empty tree"""
        mock_github_instance = Mock(spec=Github)
        mock_repo = Mock(spec=Repository)
        mock_github_instance.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github_instance

        # Make the root tree fetch raise an exception
        install_fake_github(mock_repo, {})
        mock_repo.get_git_tree.side_effect = Exception("API rate limit exceeded")

        repository = GithubRepoMetadataRepository(mock_github_config)

        with pytest.raises(Exception, match="API rate limit exceeded"):
            repository._build_directory_structure()

        # Should log error
        mock_logger.error.assert_called_once()

    @patch("tgfs.core.repository.impl.metadata.github_repo.Github")
    @patch("tgfs.core.repository.impl.metadata.github_repo.logger")
    def test_build_directory_structure_raises_on_subdirectory_errors(
        self, mock_logger, mock_github_class, mock_github_config
    ):
        """A subtree we cannot read makes the whole load fail explicitly"""
        mock_github_instance = Mock(spec=Github)
        mock_repo = Mock(spec=Repository)
        mock_github_instance.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github_instance

        tree_api, _ = install_fake_github(
            mock_repo, {"protected_dir": {"file.1": None}}
        )
        # Only a truncated root makes the loader descend at all
        tree_api.truncate_recursive(tree_api.root_sha)
        tree_api.fail("tree:protected_dir", Exception("Access denied"))

        repository = GithubRepoMetadataRepository(mock_github_config)

        with pytest.raises(Exception, match="Access denied"):
            repository._build_directory_structure()

        # Should log the failing path
        mock_logger.error.assert_called_once()
        error_call = mock_logger.error.call_args[0][0]
        assert "protected_dir" in error_call

    @pytest.mark.asyncio
    async def test_push_method(self, mock_github_config):
        """Test push method (currently no-op)"""
        with patch("tgfs.core.repository.impl.metadata.github_repo.Github"):
            repository = GithubRepoMetadataRepository(mock_github_config)
            # Should not raise any exception
            await repository.push()


class TestMetadataCache:
    """The persistent cache is strictly an optional startup accelerator."""

    SHA = "a" * 40

    @staticmethod
    def _cache_path(data_dir: Path, repo: str, channel_id: str) -> Path:
        return data_dir / "metadata-cache" / f"{repo.replace('/', '-')}-{channel_id}.json"

    @patch("tgfs.core.repository.impl.metadata.github_repo.Github")
    @pytest.mark.asyncio
    async def test_no_cache_falls_back_to_complete_github_tree_walk(
        self, mock_github_class, tmp_path
    ):
        config = GithubRepoConfig(
            repo="owner/test-repo", commit="main", access_token="token"
        )
        repository, _, tree_api, branch_api = build_repository(
            mock_github_class, config, {"report.42": None}
        )
        repository._cache_path = self._cache_path(tmp_path, config.repo, "123")

        metadata = await repository.get()

        assert metadata.dir.find_file("report").message_id == 42
        assert branch_api.calls == ["main"]
        assert tree_api.recursive_calls == [tree_api.root_sha]

    @patch("tgfs.core.repository.impl.metadata.github_repo.Github")
    @pytest.mark.asyncio
    async def test_matching_sha_pinned_cache_skips_all_github_metadata_calls(
        self, mock_github_class, tmp_path
    ):
        config = GithubRepoConfig(
            repo="owner/test-repo", commit=self.SHA, access_token="token"
        )
        repository, mock_repo, _, _ = build_repository(
            mock_github_class, config, {"ignored.1": None}
        )
        cache_path = self._cache_path(tmp_path, config.repo, "123")
        repository._cache_path = cache_path
        cached_root = GithubDirectory(repository._ghc, "root", None)
        TGFSDirectory.create_file_ref(cached_root, "cached", 9)
        write_cache(
            cache_path,
            TGFSMetadata(cached_root),
            repo=config.repo,
            configured_ref=self.SHA,
            resolved_tree_sha="tree-sha",
        )

        metadata = await repository.get()

        assert metadata.dir.find_file("cached").message_id == 9
        assert isinstance(metadata.dir, GithubDirectory)
        mock_repo.get_branch.assert_not_called()
        mock_repo.get_git_tree.assert_not_called()

    @patch("tgfs.core.repository.impl.metadata.github_repo.Github")
    @pytest.mark.asyncio
    async def test_branch_cache_checks_one_tree_sha_then_uses_matching_cache(
        self, mock_github_class, tmp_path
    ):
        config = GithubRepoConfig(
            repo="owner/test-repo", commit="main", access_token="token"
        )
        repository, mock_repo, tree_api, branch_api = build_repository(
            mock_github_class, config, {"ignored.1": None}
        )
        cache_path = self._cache_path(tmp_path, config.repo, "123")
        repository._cache_path = cache_path
        cached_root = GithubDirectory(repository._ghc, "root", None)
        TGFSDirectory.create_file_ref(cached_root, "cached", 9)
        write_cache(
            cache_path,
            TGFSMetadata(cached_root),
            repo=config.repo,
            configured_ref="main",
            resolved_tree_sha=tree_api.root_sha,
        )

        metadata = await repository.get()

        assert metadata.dir.find_file("cached").message_id == 9
        assert branch_api.calls == ["main"]
        mock_repo.get_git_tree.assert_not_called()

    @patch("tgfs.core.repository.impl.metadata.github_repo.Github")
    @pytest.mark.asyncio
    async def test_branch_cache_with_changed_tree_sha_falls_back_to_walk(
        self, mock_github_class, tmp_path
    ):
        config = GithubRepoConfig(
            repo="owner/test-repo", commit="main", access_token="token"
        )
        repository, _, tree_api, branch_api = build_repository(
            mock_github_class, config, {"fresh.10": None}
        )
        cache_path = self._cache_path(tmp_path, config.repo, "123")
        repository._cache_path = cache_path
        cached_root = GithubDirectory(repository._ghc, "root", None)
        TGFSDirectory.create_file_ref(cached_root, "stale", 9)
        write_cache(
            cache_path,
            TGFSMetadata(cached_root),
            repo=config.repo,
            configured_ref="main",
            resolved_tree_sha="old-tree-sha",
        )

        metadata = await repository.get()

        assert metadata.dir.find_file("fresh").message_id == 10
        assert branch_api.calls == ["main"]
        assert tree_api.recursive_calls == [tree_api.root_sha]

    @pytest.mark.parametrize(
        "cache_contents",
        [
            "{truncated",
            json.dumps({"cache_version": 2}),
        ],
    )
    @patch("tgfs.core.repository.impl.metadata.github_repo.Github")
    @pytest.mark.asyncio
    async def test_invalid_cache_is_ignored_and_full_walk_still_succeeds(
        self, mock_github_class, tmp_path, cache_contents
    ):
        config = GithubRepoConfig(
            repo="owner/test-repo", commit="main", access_token="token"
        )
        repository, _, tree_api, _ = build_repository(
            mock_github_class, config, {"fresh.10": None}
        )
        cache_path = self._cache_path(tmp_path, config.repo, "123")
        repository._cache_path = cache_path
        cache_path.parent.mkdir(parents=True)
        cache_path.write_text(cache_contents)

        metadata = await repository.get()

        assert metadata.dir.find_file("fresh").message_id == 10
        assert tree_api.recursive_calls == [tree_api.root_sha]

    @patch("tgfs.core.repository.impl.metadata.github_repo.Github")
    @pytest.mark.asyncio
    async def test_push_refreshes_cache_with_current_metadata_and_timestamp(
        self, mock_github_class, tmp_path
    ):
        config = GithubRepoConfig(
            repo="owner/test-repo", commit=self.SHA, access_token="token"
        )
        repository, _, _, _ = build_repository(mock_github_class, config, {})
        cache_path = self._cache_path(tmp_path, config.repo, "123")
        repository._cache_path = cache_path
        root = GithubDirectory(repository._ghc, "root", None)
        TGFSDirectory.create_file_ref(root, "current", 12)
        repository.metadata = TGFSMetadata(root)

        await repository.push()

        saved = json.loads(cache_path.read_text())
        assert saved["cache_version"] == 1
        assert saved["repo"] == config.repo
        assert saved["configured_ref"] == self.SHA
        assert saved["metadata"] == repository.metadata.to_dict()
        assert datetime.fromisoformat(saved["written_at"].replace("Z", "+00:00"))

    @patch("tgfs.core.repository.impl.metadata.github_repo.Github")
    @pytest.mark.asyncio
    async def test_cached_tree_rebuilds_github_directories_for_future_writes(
        self, mock_github_class, tmp_path
    ):
        config = GithubRepoConfig(
            repo="owner/test-repo", commit=self.SHA, access_token="token"
        )
        repository, mock_repo, _, _ = build_repository(mock_github_class, config, {})
        cache_path = self._cache_path(tmp_path, config.repo, "123")
        repository._cache_path = cache_path
        cached_root = GithubDirectory(repository._ghc, "root", None)
        child = cached_root.create_dir_skip_github_ops("documents")
        TGFSDirectory.create_file_ref(child, "prior", 1)
        write_cache(
            cache_path,
            TGFSMetadata(cached_root),
            repo=config.repo,
            configured_ref=self.SHA,
            resolved_tree_sha="tree-sha",
        )

        metadata = await repository.get()
        loaded_child = metadata.dir.find_dir("documents")
        loaded_child.create_dir("next", None)

        assert isinstance(loaded_child, GithubDirectory)
        mock_repo.create_file.assert_called_once_with(
            path="documents/next/.gitkeep",
            message="Create directory next",
            content="",
            branch=self.SHA,
        )


class TestGitTreeLoader:
    """The loader must reconstruct the whole metadata tree via the Git Trees API.

    Completeness alone is not enough: one request per directory takes >10k
    requests on the production tree and gets rate limited before the server can
    start, so every request must bring back the largest subtree GitHub will
    give, and only a truncated answer may be split any further.
    """

    # The path that went missing in production after a restart.
    DEEP_PATH = "minio-mirror/b2-eu-cen/1580559962386441/file-data/10038264"

    @staticmethod
    def _structure() -> Dict[str, Any]:
        return {
            "README.md": None,
            "minio-mirror": {
                "b2-eu-cen": {
                    "1580559962386441": {
                        "file-data": {
                            "10038264": {
                                ".gitkeep": None,
                                "mldata.271686": None,
                            },
                        },
                    },
                },
            },
        }

    @staticmethod
    def _repository(mock_github_class, mock_github_config, tree_api: FakeTreeApi):
        mock_github_instance = Mock(spec=Github)
        mock_repo = Mock(spec=Repository)
        mock_github_instance.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github_instance

        mock_repo.get_branch.side_effect = FakeBranchApi(
            {mock_github_config.commit: tree_api.root_sha}
        )
        mock_repo.get_git_tree.side_effect = tree_api
        # The contents API is what failed in production on this wide tree: it
        # must not be used (or trusted) by the loader at all.
        mock_repo.get_contents.side_effect = AssertionError(
            "loader must not use get_contents"
        )

        return GithubRepoMetadataRepository(mock_github_config), mock_repo

    @patch("tgfs.core.repository.impl.metadata.github_repo.Github")
    def test_deep_file_ref_is_reconstructed_without_get_contents(
        self, mock_github_class, mock_github_config
    ):
        """The known production path must be rebuilt purely from Git Trees calls"""
        tree_api = make_tree_api("main", self._structure())
        repository, mock_repo = self._repository(
            mock_github_class, mock_github_config, tree_api
        )

        root_dir = repository._build_directory_structure()

        node: TGFSDirectory = root_dir
        for part in self.DEEP_PATH.split("/"):
            node = node.find_dir(part)

        file_ref = node.find_file("mldata")
        assert file_ref.message_id == 271686
        assert file_ref.location is node

        # .gitkeep is a marker, never a file reference
        assert [f.name for f in node.files] == ["mldata"]
        # README.md is an unrelated blob and must not become a file ref
        assert root_dir.files == []
        mock_repo.get_contents.assert_not_called()

    @patch("tgfs.core.repository.impl.metadata.github_repo.Github")
    def test_a_complete_tree_costs_exactly_one_recursive_call(
        self, mock_github_class, mock_github_config
    ):
        """A subtree GitHub returns whole is never split into child requests"""
        tree_api = make_tree_api("main", self._structure())
        repository, _ = self._repository(
            mock_github_class, mock_github_config, tree_api
        )

        repository._build_directory_structure()

        assert tree_api.calls == [(tree_api.root_sha, True)]

    @patch("tgfs.core.repository.impl.metadata.github_repo.Github")
    def test_a_flattened_path_reuses_one_directory_per_level(
        self, mock_github_class, mock_github_config
    ):
        """A recursive listing names a directory once per entry below it"""
        tree_api = make_tree_api("main", self._structure())
        repository, _ = self._repository(
            mock_github_class, mock_github_config, tree_api
        )

        root_dir = repository._build_directory_structure()

        node: TGFSDirectory = root_dir
        for part in self.DEEP_PATH.split("/"):
            assert [child.name for child in node.children] == [part]
            node = node.children[0]
        assert node.children == []

    @patch("tgfs.core.repository.impl.metadata.github_repo.Github")
    def test_large_deep_complete_tree_costs_exactly_one_recursive_call(
        self, mock_github_class, mock_github_config
    ):
        """A wide, deep tree is one request, not one per directory"""
        structure: Dict[str, Any] = {}
        expected_leaves = []
        for bucket in range(40):
            leaf: Dict[str, Any] = {
                ".gitkeep": None,
                f"blob-{bucket}.{1000 + bucket}": None,
            }
            structure[f"bucket-{bucket}"] = {
                "b2-eu-cen": {f"{bucket}0000000000": {"file-data": leaf}}
            }
            expected_leaves.append(
                f"bucket-{bucket}/b2-eu-cen/{bucket}0000000000/file-data"
            )

        tree_api = make_tree_api("main", structure)
        repository, mock_repo = self._repository(
            mock_github_class, mock_github_config, tree_api
        )

        root_dir = repository._build_directory_structure()

        assert tree_api.calls == [(tree_api.root_sha, True)]
        assert mock_repo.get_branch.call_count == 1

        for bucket, path in enumerate(expected_leaves):
            node: TGFSDirectory = root_dir
            for part in path.split("/"):
                node = node.find_dir(part)
            assert node.find_file(f"blob-{bucket}").message_id == 1000 + bucket
            assert [f.name for f in node.files] == [f"blob-{bucket}"]

    @patch("tgfs.core.repository.impl.metadata.github_repo.Github")
    def test_twenty_thousand_metadata_refs_load_in_one_complete_tree_request(
        self, mock_github_class, mock_github_config
    ):
        """Production-scale complete metadata must not cause per-directory calls.

        This is intentionally 20,000 file refs, spread over 100 directory
        branches.  It models the old stalled backup without relying on timing
        thresholds that would make CI flaky: the API call count is the actual
        scalability contract.
        """
        files_per_bucket = 200
        bucket_count = 100
        structure: Dict[str, Any] = {}
        for bucket in range(bucket_count):
            files: Dict[str, Any] = {".gitkeep": None}
            for number in range(files_per_bucket):
                message_id = bucket * files_per_bucket + number + 1
                files[f"object-{bucket:03d}-{number:03d}.{message_id}"] = None
            structure[f"bucket-{bucket:03d}"] = {
                "b2-eu-cen": {f"{bucket:016d}": {"file-data": files}}
            }

        tree_api = make_tree_api("main", structure)
        repository, mock_repo = self._repository(
            mock_github_class, mock_github_config, tree_api
        )

        root_dir = repository._build_directory_structure()

        # One branch resolution + precisely one complete recursive tree fetch;
        # any per-directory traversal would fail this assertion.
        assert mock_repo.get_branch.call_count == 1
        assert tree_api.calls == [(tree_api.root_sha, True)]

        # Verify both total cardinality and representative refs across the tree.
        total_refs = 0
        for bucket in range(bucket_count):
            node = root_dir.find_dir(f"bucket-{bucket:03d}")
            node = node.find_dir("b2-eu-cen")
            node = node.find_dir(f"{bucket:016d}")
            node = node.find_dir("file-data")
            total_refs += len(node.files)
            for number in (0, files_per_bucket - 1):
                message_id = bucket * files_per_bucket + number + 1
                assert (
                    node.find_file(f"object-{bucket:03d}-{number:03d}").message_id
                    == message_id
                )
        assert total_refs == bucket_count * files_per_bucket

    @patch("tgfs.core.repository.impl.metadata.github_repo.Github")
    def test_truncated_root_falls_back_to_children_and_stays_complete(
        self, mock_github_class, mock_github_config
    ):
        """A truncated root is split at its immediate children, never reconstructed"""
        tree_api = make_tree_api("main", self._structure())
        tree_api.truncate_recursive(tree_api.root_sha)

        repository, _ = self._repository(
            mock_github_class, mock_github_config, tree_api
        )

        root_dir = repository._build_directory_structure()

        assert tree_api.calls == [
            (tree_api.root_sha, True),
            (tree_api.root_sha, False),
            ("tree:minio-mirror", True),
        ]

        node: TGFSDirectory = root_dir
        for part in self.DEEP_PATH.split("/"):
            node = node.find_dir(part)
        assert node.find_file("mldata").message_id == 271686
        assert [f.name for f in node.files] == ["mldata"]

    @patch("tgfs.core.repository.impl.metadata.github_repo.Github")
    def test_only_the_truncated_subtree_is_split_further(
        self, mock_github_class, mock_github_config
    ):
        """Splitting stops as soon as a level answers completely"""
        tree_api = make_tree_api("main", self._structure())
        tree_api.truncate_recursive(tree_api.root_sha)
        tree_api.truncate_recursive("tree:minio-mirror")

        repository, _ = self._repository(
            mock_github_class, mock_github_config, tree_api
        )

        root_dir = repository._build_directory_structure()

        assert tree_api.calls == [
            (tree_api.root_sha, True),
            (tree_api.root_sha, False),
            ("tree:minio-mirror", True),
            ("tree:minio-mirror", False),
            ("tree:minio-mirror/b2-eu-cen", True),
        ]

        node: TGFSDirectory = root_dir
        for part in self.DEEP_PATH.split("/"):
            node = node.find_dir(part)
        assert node.find_file("mldata").message_id == 271686

    @patch("tgfs.core.repository.impl.metadata.github_repo.Github")
    def test_missing_subtree_is_not_silently_swallowed(
        self, mock_github_class, mock_github_config
    ):
        """A subtree that cannot be fetched must raise, never yield a partial tree"""
        tree_api = make_tree_api("main", self._structure())
        tree_api.truncate_recursive(tree_api.root_sha)
        tree_api.forget("tree:minio-mirror")

        repository, _ = self._repository(
            mock_github_class, mock_github_config, tree_api
        )

        with pytest.raises(GithubException):
            repository._build_directory_structure()

    @patch("tgfs.core.repository.impl.metadata.github_repo.Github")
    def test_truncated_nonrecursive_fallback_is_reported_as_an_error(
        self, mock_github_class, mock_github_config
    ):
        """A tree too large even to list its children cannot be loaded at all"""
        tree_api = make_tree_api("main", self._structure())
        tree_api.truncate_completely(tree_api.root_sha)

        repository, _ = self._repository(
            mock_github_class, mock_github_config, tree_api
        )

        with pytest.raises(TechnicalError, match="truncated") as excinfo:
            repository._build_directory_structure()

        assert "/" in str(excinfo.value)

    @patch("tgfs.core.repository.impl.metadata.github_repo.Github")
    def test_truncated_nonrecursive_fallback_names_the_failing_path(
        self, mock_github_class, mock_github_config
    ):
        """The failing subtree is named so the metadata repo can be fixed"""
        tree_api = make_tree_api("main", self._structure())
        tree_api.truncate_recursive(tree_api.root_sha)
        tree_api.truncate_completely("tree:minio-mirror")

        repository, _ = self._repository(
            mock_github_class, mock_github_config, tree_api
        )

        with pytest.raises(TechnicalError, match="truncated") as excinfo:
            repository._build_directory_structure()

        assert "minio-mirror" in str(excinfo.value)


class TestNonRepresentableEntries:
    """Valid GitHub content TGFS cannot model must not abort the whole load.

    Only an unreadable or truncated tree means the metadata we fetched is
    untrustworthy. An entry we simply cannot put in the in-memory model is a
    content problem: warn, skip it, and keep the rest of that tree.
    """

    @patch("tgfs.core.repository.impl.metadata.github_repo.logger")
    @patch("tgfs.core.repository.impl.metadata.github_repo.Github")
    def test_duplicate_file_names_are_skipped_and_the_rest_of_the_tree_loads(
        self, mock_github_class, mock_logger, mock_github_config
    ):
        """Two blobs mapping to one file ref name: keep one, warn, keep loading"""
        repository, _, _, _ = build_repository(
            mock_github_class,
            mock_github_config,
            {"foo.111": None, "foo.222": None, "bar.333": None},
        )

        root_dir = repository._build_directory_structure()

        assert [f.name for f in root_dir.files] == ["foo", "bar"]
        assert root_dir.find_file("foo").message_id == 111
        assert root_dir.find_file("bar").message_id == 333

        warnings = [call[0][0] for call in mock_logger.warning.call_args_list]
        assert any("foo.222" in warning for warning in warnings), warnings
        mock_logger.error.assert_not_called()

    @patch("tgfs.core.repository.impl.metadata.github_repo.logger")
    @patch("tgfs.core.repository.impl.metadata.github_repo.Github")
    def test_invalid_directory_name_is_skipped_and_valid_sibling_loads(
        self, mock_github_class, mock_logger, mock_github_config
    ):
        """A directory name TGFS rejects must not stop its siblings from loading"""
        repository, _, tree_api, _ = build_repository(
            mock_github_class,
            mock_github_config,
            {
                "-weird": {"hidden.1": None},
                "good": {"kept.2": None},
            },
        )

        root_dir = repository._build_directory_structure()

        assert [child.name for child in root_dir.children] == ["good"]
        good = root_dir.find_dir("good")
        assert [f.name for f in good.files] == ["kept"]

        # The rejected directory is never even fetched
        assert "tree:-weird" not in [sha for sha, _ in tree_api.calls]

        warnings = [call[0][0] for call in mock_logger.warning.call_args_list]
        assert any("-weird" in warning for warning in warnings), warnings
        mock_logger.error.assert_not_called()

    @patch("tgfs.core.repository.impl.metadata.github_repo.logger")
    @patch("tgfs.core.repository.impl.metadata.github_repo.Github")
    def test_invalid_component_of_a_flattened_path_keeps_valid_paths(
        self, mock_github_class, mock_logger, mock_github_config
    ):
        """A recursive listing names nested paths; one bad component drops only itself"""
        repository, _, _, _ = build_repository(
            mock_github_class,
            mock_github_config,
            {
                "-bad": {"deep": {"lost.1": None}},
                "a": {"b": {"kept.2": None}},
            },
        )

        root_dir = repository._build_directory_structure()

        assert [child.name for child in root_dir.children] == ["a"]
        deep = root_dir.find_dir("a").find_dir("b")
        assert [f.name for f in deep.files] == ["kept"]
        assert deep.find_file("kept").message_id == 2

        warnings = [call[0][0] for call in mock_logger.warning.call_args_list]
        assert any("-bad" in warning for warning in warnings), warnings
        mock_logger.error.assert_not_called()

    @patch("tgfs.core.repository.impl.metadata.github_repo.Github")
    def test_truncated_nested_tree_is_not_swallowed(
        self, mock_github_class, mock_github_config
    ):
        """Skipping unrepresentable entries must not soften truncation anywhere"""
        repository, _, tree_api, _ = build_repository(
            mock_github_class,
            mock_github_config,
            {"outer": {"inner": {"file.1": None}}},
        )
        tree_api.truncate_recursive(tree_api.root_sha)
        tree_api.truncate_recursive("tree:outer")
        tree_api.truncate_completely("tree:outer/inner")

        with pytest.raises(Exception, match="truncated") as excinfo:
            repository._build_directory_structure()

        assert "outer/inner" in str(excinfo.value)


class TestRefResolution:
    """The configured ref must become a tree SHA before any Git Trees call.

    ``get_git_tree`` puts its argument in one URL path segment (PyGithub quotes
    it with ``safe=""``), so a branch such as ``metadata/main`` would be sent as
    ``metadata%2Fmain`` and never resolve.
    """

    @staticmethod
    def _config(commit: str) -> GithubRepoConfig:
        return GithubRepoConfig(
            access_token="test_token", repo="owner/test-repo", commit=commit
        )

    @patch("tgfs.core.repository.impl.metadata.github_repo.Github")
    def test_slashed_branch_is_resolved_to_a_tree_sha(self, mock_github_class):
        """A branch name with a slash is resolved, never handed to get_git_tree"""
        config = self._config("metadata/main")
        repository, _, tree_api, branch_api = build_repository(
            mock_github_class, config, {"doc.1": None}
        )

        assert repository._ghc.commit == "metadata/main"

        root_dir = repository._build_directory_structure()

        assert branch_api.calls == ["metadata/main"]
        assert tree_api.calls[0][0] == root_tree_sha("metadata/main")
        assert "metadata/main" not in [sha for sha, _ in tree_api.calls]

        assert [f.name for f in root_dir.files] == ["doc"]

    @patch("tgfs.core.repository.impl.metadata.github_repo.Github")
    def test_ref_is_resolved_once_for_the_whole_walk(self, mock_github_class):
        """Subtrees are fetched by SHA, so resolution must not repeat per level"""
        config = self._config("metadata/main")
        repository, _, tree_api, branch_api = build_repository(
            mock_github_class,
            config,
            {"a": {"b": {"c": {"deep.1": None}}}},
        )

        repository._build_directory_structure()

        assert branch_api.calls == ["metadata/main"]
        assert tree_api.calls == [(root_tree_sha("metadata/main"), True)]

    @patch("tgfs.core.repository.impl.metadata.github_repo.Github")
    def test_plain_branch_name_is_resolved_the_same_way(self, mock_github_class):
        """An ordinary branch config keeps working through the same resolution"""
        config = self._config("main")
        repository, _, tree_api, branch_api = build_repository(
            mock_github_class, config, {"sub": {"doc.1": None}}
        )

        root_dir = repository._build_directory_structure()

        assert branch_api.calls == ["main"]
        assert [sha for sha, _ in tree_api.calls] == [root_tree_sha("main")]
        assert [f.name for f in root_dir.find_dir("sub").files] == ["doc"]


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

    def test_create_dir_conflict_with_existing_marker_is_idempotent(self, mock_ghc):
        """422 + the exact .gitkeep already present => success, child retained"""
        mock_ghc.repo.create_file.side_effect = conflict_422()
        mock_ghc.repo.get_contents.return_value = existing_content("child/.gitkeep")

        parent_dir = GithubDirectory(mock_ghc, "parent", None)
        child_dir = parent_dir.create_dir("child")

        mock_ghc.repo.get_contents.assert_called_once_with("child/.gitkeep", ref="main")

        assert isinstance(child_dir, GithubDirectory)
        assert child_dir.name == "child"
        assert child_dir.parent == parent_dir
        assert parent_dir.children == [child_dir]

    def test_create_dir_conflict_without_confirmed_marker_raises(self, mock_ghc):
        """422 but the exact .gitkeep cannot be read back => raise and roll back"""
        mock_ghc.repo.create_file.side_effect = conflict_422()
        mock_ghc.repo.get_contents.side_effect = GithubException(
            404, data={"message": "Not Found"}
        )

        parent_dir = GithubDirectory(mock_ghc, "parent", None)

        with pytest.raises(GithubException) as excinfo:
            parent_dir.create_dir("child")

        assert excinfo.value.status == 422
        assert parent_dir.children == []

    def test_create_dir_conflict_with_different_path_raises(self, mock_ghc):
        """A read that returns some other path does not confirm the marker"""
        mock_ghc.repo.create_file.side_effect = conflict_422()
        mock_ghc.repo.get_contents.return_value = [
            existing_content("child/something-else.1")
        ]

        parent_dir = GithubDirectory(mock_ghc, "parent", None)

        with pytest.raises(GithubException):
            parent_dir.create_dir("child")

        assert parent_dir.children == []

    def test_create_dir_non_conflict_error_raises_even_if_marker_exists(self, mock_ghc):
        """Only a 422 conflict is idempotent; other failures always propagate"""
        mock_ghc.repo.create_file.side_effect = GithubException(
            500, data={"message": "Server Error"}
        )
        mock_ghc.repo.get_contents.return_value = existing_content("child/.gitkeep")

        parent_dir = GithubDirectory(mock_ghc, "parent", None)

        with pytest.raises(GithubException) as excinfo:
            parent_dir.create_dir("child")

        assert excinfo.value.status == 500
        assert parent_dir.children == []
        mock_ghc.repo.get_contents.assert_not_called()

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

    def test_create_file_ref_conflict_with_existing_reference_is_idempotent(
        self, mock_ghc
    ):
        """422 + the exact name.message_id already present => success, ref retained"""
        mock_ghc.repo.create_file.side_effect = conflict_422()
        mock_ghc.repo.get_contents.return_value = existing_content("testfile.12345")

        directory = GithubDirectory(mock_ghc, "testdir", None)
        file_ref = directory.create_file_ref("testfile", 12345)

        mock_ghc.repo.get_contents.assert_called_once_with("testfile.12345", ref="main")

        assert isinstance(file_ref, TGFSFileRef)
        assert file_ref.name == "testfile"
        assert file_ref.message_id == 12345
        assert directory.files == [file_ref]

    def test_create_file_ref_conflict_with_different_message_id_raises(self, mock_ghc):
        """A same-named reference with another message id must not count as ours"""
        mock_ghc.repo.create_file.side_effect = conflict_422()
        mock_ghc.repo.get_contents.return_value = existing_content("testfile.99999")

        directory = GithubDirectory(mock_ghc, "testdir", None)

        with pytest.raises(GithubException) as excinfo:
            directory.create_file_ref("testfile", 12345)

        assert excinfo.value.status == 422
        assert directory.files == []

    def test_create_file_ref_conflict_without_confirmed_reference_raises(
        self, mock_ghc
    ):
        """422 but the read fails => raise and roll back the tentative file ref"""
        mock_ghc.repo.create_file.side_effect = conflict_422()
        mock_ghc.repo.get_contents.side_effect = GithubException(
            404, data={"message": "Not Found"}
        )

        directory = GithubDirectory(mock_ghc, "testdir", None)

        with pytest.raises(GithubException):
            directory.create_file_ref("testfile", 12345)

        assert directory.files == []

    def test_create_file_ref_non_conflict_error_raises_even_if_present(self, mock_ghc):
        """Only a 422 conflict is idempotent; other failures always propagate"""
        mock_ghc.repo.create_file.side_effect = GithubException(
            500, data={"message": "Server Error"}
        )
        mock_ghc.repo.get_contents.return_value = existing_content("testfile.12345")

        directory = GithubDirectory(mock_ghc, "testdir", None)

        with pytest.raises(GithubException) as excinfo:
            directory.create_file_ref("testfile", 12345)

        assert excinfo.value.status == 500
        assert directory.files == []
        mock_ghc.repo.get_contents.assert_not_called()

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
        install_fake_github(mock_repo, {})

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
        install_fake_github(
            mock_repo,
            {
                "docs": {
                    "2023": {
                        "reports": {
                            "q1_report.111": None,
                            "q2_report.222": None,
                        }
                    }
                }
            },
        )

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
        # Non-numeric message ID
        install_fake_github(mock_ghc.repo, {"test.abc": None})

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
        install_fake_github(mock_ghc.repo, {})

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
        install_fake_github(
            mock_ghc.repo,
            {
                ".gitkeep": None,
                "subdir": {".gitkeep": None},
            },
        )

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

    def test_single_tree_entry(self, mock_ghc):
        """Test handling of a tree holding a single entry"""
        install_fake_github(mock_ghc.repo, {"single.123": None})

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

    def test_unsupported_tree_entry_type_is_ignored(self, mock_ghc):
        """Submodules and other non blob/tree entries are not part of metadata"""
        install_fake_github(mock_ghc.repo, {"submodule": SUBMODULE, "single.123": None})

        with patch("tgfs.core.repository.impl.metadata.github_repo.Github"):
            repository = GithubRepoMetadataRepository(
                GithubRepoConfig(access_token="test", repo="test/repo", commit="main")
            )
            repository._ghc = mock_ghc

            root_dir = repository._build_directory_structure()

            assert len(root_dir.children) == 0
            assert len(root_dir.files) == 1
            assert root_dir.files[0].name == "single"
