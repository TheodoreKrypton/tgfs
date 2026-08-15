import logging

from github import Github
from github.GitTree import GitTree
from github.GitTreeElement import GitTreeElement

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

    async def push(self) -> None:
        pass

    async def get(self) -> TGFSMetadata:
        root_dir = self._build_directory_structure()
        return TGFSMetadata(dir=root_dir)

    def _build_directory_structure(self) -> GithubDirectory:
        root = GithubDirectory(
            self._ghc, name="root", parent=None, children=[], files=[]
        )

        try:
            root_tree = self._get_tree(self._resolve_root_tree_sha(), path="")
        except Exception as ex:
            logger.error(f"Failed to read the metadata root tree: {ex}")
            raise

        self._walk_tree(root_tree, root, path="")

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

    def _get_tree(self, tree_sha: str, path: str) -> GitTree:
        """Fetch a single tree level.

        The tree is walked one level at a time: a recursive listing (either
        through the contents API or ``recursive=True``) is silently truncated by
        GitHub once the metadata tree gets wide enough, which would make the
        loader drop existing directories.
        """
        tree = self._ghc.repo.get_git_tree(tree_sha, recursive=False)

        if tree.truncated:
            raise TechnicalError(
                f"The metadata tree at '{path or '/'}' was truncated by GitHub, "
                "so it cannot be loaded completely"
            )

        return tree

    def _walk_tree(self, tree: GitTree, parent_dir: GithubDirectory, path: str) -> None:
        for element in tree.tree:
            name = element.path.rsplit("/", 1)[-1]
            element_path = f"{path}/{name}" if path else name

            if element.type == "tree":
                self._add_child_dir(element, name, element_path, parent_dir)
            elif element.type == "blob":
                self._add_file_ref(name, element_path, parent_dir)
            else:
                logger.warning(
                    f"Ignoring unsupported entry {element_path} of type {element.type}"
                )

    def _add_child_dir(
        self,
        element: GitTreeElement,
        name: str,
        path: str,
        parent_dir: GithubDirectory,
    ) -> None:
        try:
            child_dir = self._create_child_dir(name, parent_dir)
        except (FileOrDirectoryAlreadyExists, InvalidName) as ex:
            # Content TGFS cannot represent is not a broken metadata read: the
            # rest of this tree is still trustworthy, so only this entry (and
            # everything below it) is dropped.
            logger.warning(f"Skipping directory {path}: {ex}")
            return

        try:
            child_tree = self._get_tree(element.sha, path=path)
        except Exception as ex:
            # A subtree we cannot read means an incomplete metadata graph, which
            # later makes TGFS try to recreate directories that already exist.
            logger.error(f"Failed to construct directory {path}: {ex}")
            raise

        self._walk_tree(child_tree, child_dir, path=path)

    def _create_child_dir(
        self, name: str, parent_dir: GithubDirectory
    ) -> GithubDirectory:
        child_dir = GithubDirectory(self._ghc, name, parent_dir)
        parent_dir.children.append(child_dir)
        return child_dir

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
