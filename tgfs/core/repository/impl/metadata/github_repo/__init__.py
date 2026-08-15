import logging
from typing import Optional

from github import Github
from github.GitTree import GitTree

from tgfs.config import GithubRepoConfig
from tgfs.core.model import TGFSDirectory, TGFSMetadata
from tgfs.core.repository.interface import IMetaDataRepository
from tgfs.errors import FileOrDirectoryAlreadyExists, InvalidName, TechnicalError

from .gh_directory import GithubConfig, GithubDirectory

logger = logging.getLogger(__name__)

GITKEEP = ".gitkeep"


class GithubRepoMetadataRepository(IMetaDataRepository):
    def __init__(self, config: GithubRepoConfig):
        super().__init__()

        gh = Github(config.access_token)

        self._ghc = GithubConfig(
            gh=gh,
            repo_name=config.repo,
            repo=gh.get_repo(config.repo),
            commit=config.commit,
        )

        # State of the load in progress: every directory built so far, by path,
        # and the ones dropped, so each is reported once even though a recursive
        # listing names them again for every entry below them.
        self._dirs_by_path: dict[str, GithubDirectory] = {}
        self._skipped_dirs: set[str] = set()

    async def push(self) -> None:
        pass

    async def get(self) -> TGFSMetadata:
        root_dir = self._build_directory_structure()
        return TGFSMetadata(dir=root_dir)

    def _build_directory_structure(self) -> GithubDirectory:
        root = GithubDirectory(
            self._ghc, name="root", parent=None, children=[], files=[]
        )

        self._dirs_by_path = {"": root}
        self._skipped_dirs.clear()

        self._load_subtree(self._resolve_root_tree_sha(), root, path="")

        return root

    def _resolve_root_tree_sha(self) -> str:
        """Turn the configured ref into the SHA of the commit's root tree.

        ``get_git_tree`` sends its argument as a single URL path segment, so a
        branch name containing a slash ('metadata/main') would arrive at GitHub
        percent encoded and never resolve. The branches API does accept such
        names and its payload already carries the root tree SHA, so one call
        here is enough for the whole walk: every subtree below is fetched by
        SHA anyway.
        """
        ref = self._ghc.commit

        try:
            return self._ghc.repo.get_branch(ref).commit.commit.tree.sha
        except Exception as ex:
            # The ref may well be a commit SHA or a tag rather than a branch;
            # the trees API takes those verbatim, so keep the configured value.
            logger.warning(
                f"Could not resolve '{ref}' as a branch ({ex}), "
                "using it as a tree-ish instead"
            )
            return ref

    def _fetch_tree(self, tree_sha: str, path: str, recursive: bool) -> GitTree:
        try:
            return self._ghc.repo.get_git_tree(tree_sha, recursive=recursive)
        except Exception as ex:
            # A subtree we cannot read means an incomplete metadata graph, which
            # later makes TGFS try to recreate directories that already exist.
            logger.error(f"Failed to read the metadata tree at '{path or '/'}': {ex}")
            raise

    def _load_subtree(
        self, tree_sha: str, directory: GithubDirectory, path: str
    ) -> None:
        """Load a tree and everything below it in as few requests as possible.

        One request per directory costs thousands of calls on a metadata
        repository of this size and gets rate limited long before the walk ends,
        so every subtree is first asked for recursively: that brings back a
        whole branch of the metadata in a single request.

        GitHub silently truncates a listing that is too large, and a truncated
        listing must never be reconstructed from - it would drop existing
        directories. Such a subtree is instead split at its immediate children,
        each of which is loaded the very same way.
        """
        recursive_tree = self._fetch_tree(tree_sha, path, recursive=True)

        if not recursive_tree.truncated:
            self._add_flattened_tree(recursive_tree, directory, path)
            return

        logger.info(
            f"The metadata tree at '{path or '/'}' is too large for a single "
            "listing, loading its children separately"
        )

        tree = self._fetch_tree(tree_sha, path, recursive=False)

        if tree.truncated:
            # Nothing left to split it into: this is as small as a request gets.
            raise TechnicalError(
                f"The metadata tree at '{path or '/'}' was truncated by GitHub, "
                "so it cannot be loaded completely"
            )

        for element in tree.tree:
            name = element.path.rsplit("/", 1)[-1]
            element_path = self._join(path, name)

            if element.type == "tree":
                child_dir = self._child_dir(directory, name, element_path)
                if child_dir is not None:
                    self._load_subtree(element.sha, child_dir, element_path)
            elif element.type == "blob":
                self._add_file_ref(name, element_path, directory)
            else:
                logger.warning(
                    f"Ignoring unsupported entry {element_path} of type {element.type}"
                )

    def _add_flattened_tree(
        self, tree: GitTree, directory: GithubDirectory, path: str
    ) -> None:
        """Build every ref a complete recursive listing describes.

        ``element.path`` is relative to the fetched tree and may name several
        levels at once ('a/b/c.1'), so the directories along the way are created
        (or reused) as they are met: the listing is free to name a blob before
        the tree that holds it.
        """
        for element in tree.tree:
            parts = [part for part in element.path.split("/") if part]
            if not parts:
                continue

            element_path = self._join(path, element.path)

            if element.type not in ("tree", "blob"):
                logger.warning(
                    f"Ignoring unsupported entry {element_path} of type {element.type}"
                )
                continue

            parent_dir = self._descend(directory, parts[:-1], path)
            if parent_dir is None:
                # A directory on the way could not be represented; it was
                # already reported and everything below it goes with it.
                continue

            if element.type == "tree":
                self._child_dir(parent_dir, parts[-1], element_path)
            else:
                self._add_file_ref(parts[-1], element_path, parent_dir)

    def _descend(
        self, directory: GithubDirectory, parts: list[str], path: str
    ) -> Optional[GithubDirectory]:
        """Walk down the intermediate directories of a path, creating what is missing"""
        current = directory
        current_path = path

        for part in parts:
            current_path = self._join(current_path, part)
            child_dir = self._child_dir(current, part, current_path)
            if child_dir is None:
                return None
            current = child_dir

        return current

    def _child_dir(
        self, parent_dir: GithubDirectory, name: str, path: str
    ) -> Optional[GithubDirectory]:
        """The child directory of this path, reused if an earlier entry made it already.

        Directories are looked up by path rather than by scanning the parent:
        a flattened listing names the same directory once per entry below it, and
        scanning would turn a wide directory into quadratic work.

        Returns None for content TGFS cannot represent, which is not a broken
        metadata read: the rest of this tree is still trustworthy, so only this
        entry (and everything below it) is dropped.
        """
        if path in self._skipped_dirs:
            return None

        loaded = self._dirs_by_path.get(path)
        if loaded is not None:
            return loaded

        try:
            # The plain constructor is used on purpose: loading the metadata
            # must never write to GitHub.
            child_dir = GithubDirectory(self._ghc, name, parent_dir)
        except (FileOrDirectoryAlreadyExists, InvalidName) as ex:
            self._warn_skipped_dir(path, ex)
            return None

        parent_dir.children.append(child_dir)
        self._dirs_by_path[path] = child_dir
        return child_dir

    def _warn_skipped_dir(self, path: str, ex: Exception) -> None:
        """Report a dropped directory once, however many entries mention it"""
        self._skipped_dirs.add(path)
        logger.warning(f"Skipping directory {path}: {ex}")

    @staticmethod
    def _join(path: str, name: str) -> str:
        return f"{path}/{name}" if path else name

    @staticmethod
    def _add_file_ref(name: str, path: str, parent_dir: GithubDirectory) -> None:
        if name == GITKEEP:
            return

        try:
            file_name, message_id = name.rsplit(".", 1)
            # The base implementation is used on purpose: loading the metadata
            # must never write to GitHub.
            TGFSDirectory.create_file_ref(parent_dir, file_name, int(message_id))
        except ValueError:
            logger.warning(
                f"Invalid name format for {name}, expected a format like 'name.message_id'"
            )
        except (FileOrDirectoryAlreadyExists, InvalidName) as ex:
            # Several blobs can map to one file ref name (foo.111 and foo.222);
            # keep the first one and carry on loading the rest of the tree.
            logger.warning(f"Skipping file reference {path}: {ex}")
