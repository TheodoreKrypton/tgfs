import logging
from dataclasses import dataclass
from typing import Optional

from github import Github, GithubException
from github.Repository import Repository

from tgfs.core.model import TGFSDirectory, TGFSFileRef

logger = logging.getLogger(__name__)

# GitHub answers a create_file call for an already existing path with a 422
# complaining that "sha" wasn't supplied.
CONFLICT_STATUS = 422


@dataclass
class GithubConfig:
    gh: Github
    repo_name: str
    repo: Repository
    commit: str


class GithubDirectory(TGFSDirectory):
    def __init__(
        self,
        ghc: GithubConfig,
        name: str,
        parent: Optional[TGFSDirectory],
        children: Optional[list[TGFSDirectory]] = None,
        files: Optional[list[TGFSFileRef]] = None,
    ):
        super().__init__(name, parent, children or [], files or [])
        self._ghc = ghc

    @staticmethod
    def join_path(*args: str) -> str:
        """Join paths in a way that is compatible with GitHub"""
        return "/".join(part.strip("/") for part in args if part)

    @property
    def _github_path(self) -> str:
        """Get the GitHub repository path for this directory"""
        if self.parent is None:
            return ""

        if isinstance(self.parent, GithubDirectory):
            parent_path = self.parent._github_path
        else:
            parent_path = ""

        return self.join_path(parent_path, self.name)

    @staticmethod
    def _is_conflict(ex: Exception) -> bool:
        return isinstance(ex, GithubException) and ex.status == CONFLICT_STATUS

    def _file_exists(self, path: str) -> bool:
        """Check that this exact path already exists as a file at the configured ref"""
        try:
            contents = self._ghc.repo.get_contents(path, ref=self._ghc.commit)
        except Exception as ex:
            logger.warning(f"Could not confirm whether {path} exists: {ex}")
            return False

        if not isinstance(contents, list):
            contents = [contents]

        return any(
            content.path == path and content.type == "file" for content in contents
        )

    def _create_file_idempotent(self, path: str, message: str) -> None:
        """Create a file, tolerating a conflict when this exact path already exists.

        Anything else (including a conflict we cannot explain) is re-raised so
        the caller can roll back its tentative in-memory object.
        """
        try:
            self._ghc.repo.create_file(
                path=path,
                message=message,
                content="",
                branch=self._ghc.commit,
            )
        except Exception as ex:
            if self._is_conflict(ex) and self._file_exists(path):
                logger.info(
                    f"{path} already exists in GitHub, keeping the existing one"
                )
                return
            raise

    @classmethod
    def from_serialized(
        cls, data: dict, ghc: GithubConfig, parent: Optional["GithubDirectory"] = None
    ) -> "GithubDirectory":
        """Rebuild a cached tree without issuing GitHub write operations."""
        directory = cls(ghc, data["name"], parent, children=[], files=[])
        directory.files = [
            TGFSFileRef(
                message_id=file["messageId"], name=file["name"], location=directory
            )
            for file in data.get("files", [])
            if file.get("name") and file.get("messageId")
        ]
        directory.children = [
            cls.from_serialized(child, ghc, directory)
            for child in data.get("children", [])
        ]
        return directory

    def create_dir_skip_github_ops(self, name: str) -> "GithubDirectory":
        res = GithubDirectory(self._ghc, name, self)
        self.children.append(res)
        return res

    def create_dir(
        self, name: str, dir_to_copy: Optional[TGFSDirectory] = None
    ) -> "GithubDirectory":
        child = super().create_dir(name, dir_to_copy)

        # Create directory in GitHub by creating a placeholder file
        dir_path = self.join_path(self._github_path, name, ".gitkeep")
        try:
            self._create_file_idempotent(dir_path, f"Create directory {name}")
            logger.info(f"Created directory {name} in GitHub repository at {dir_path}")
        except Exception as ex:
            logger.error(f"Failed to create directory {name} in GitHub: {ex}")
            self.children.remove(child)
            raise

        # Convert the child to GithubDirectory
        github_child = GithubDirectory(
            ghc=self._ghc,
            name=child.name,
            parent=self,
            children=child.children,
            files=child.files,
        )

        # Replace the child in the parent's children list
        child_index = self.children.index(child)
        self.children[child_index] = github_child

        return github_child

    def delete(self) -> None:
        if self.parent:
            # Remove all files and subdirectories from GitHub
            self._delete_github_directory()
        super().delete()

    def create_file_ref(self, name: str, file_message_id: int) -> TGFSFileRef:
        file_ref = super().create_file_ref(name, file_message_id)

        # Create file reference in GitHub
        file_path = self.join_path(self._github_path, f"{name}.{file_message_id}")
        try:
            self._create_file_idempotent(file_path, f"Create file reference for {name}")
            logger.info(
                f"Created file reference {name} in {self._ghc.repo_name} at {file_path}"
            )
        except Exception as ex:
            logger.error(
                f"Failed to create file reference {name} in {self._ghc.repo_name}: {ex}"
            )
            self.files.remove(file_ref)
            raise

        return file_ref

    def delete_file_ref(self, fr: TGFSFileRef) -> None:
        # Remove file reference from GitHub
        file_path = self.join_path(self._github_path, f"{fr.name}.{fr.message_id}")
        try:
            file_content = self._ghc.repo.get_contents(file_path, ref=self._ghc.commit)
            if isinstance(file_content, list):
                file_content = file_content[0]
            self._ghc.repo.delete_file(
                path=file_path,
                message=f"Delete file reference for {fr.name}",
                sha=file_content.sha,
                branch=self._ghc.commit,
            )
            logger.info(f"Deleted file reference {fr.name} from {self._ghc.repo_name}")
        except Exception as ex:
            logger.error(
                f"Failed to delete file reference {fr.name} from {self._ghc.repo_name}: {ex}"
            )

        super().delete_file_ref(fr)

    def _delete_github_directory(self) -> None:
        """Delete all contents of this directory from GitHub"""
        try:
            # Get all contents in this directory
            contents = self._ghc.repo.get_contents(
                self._github_path, ref=self._ghc.commit
            )
            if not isinstance(contents, list):
                contents = [contents]

            # Delete all files and subdirectories
            for content in contents:
                try:
                    self._ghc.repo.delete_file(
                        path=content.path,
                        message=f"Delete {content.path}",
                        sha=content.sha,
                        branch=self._ghc.commit,
                    )
                    logger.info(f"Deleted {content.path} from {self._ghc.repo_name}")
                except Exception as ex:
                    logger.error(
                        f"Failed to delete {content.path} from {self._ghc.repo_name}: {ex}"
                    )

        except Exception as ex:
            logger.error(
                f"Failed to delete directory {self._github_path} from {self._ghc.repo_name}: {ex}"
            )
