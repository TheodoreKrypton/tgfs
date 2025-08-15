import logging
from dataclasses import dataclass
from typing import Optional

from github import Github
from github.Repository import Repository

from tgfs.core.model import TGFSDirectory, TGFSFileRef

logger = logging.getLogger(__name__)


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
            self._ghc.repo.create_file(
                path=dir_path,
                message=f"Create directory {name}",
                content="",
                branch=self._ghc.commit,
            )
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
            self._ghc.repo.create_file(
                path=file_path,
                message=f"Create file reference for {name}",
                content="",
                branch=self._ghc.commit,
            )
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
