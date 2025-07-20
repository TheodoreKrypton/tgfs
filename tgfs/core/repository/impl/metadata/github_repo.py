import logging

from github import Github
from github.ContentFile import ContentFile

from tgfs.config import GithubRepoConfig
from tgfs.core.model import TGFSMetadata, TGFSDirectory
from tgfs.core.repository.interface import IMetaDataRepository


logger = logging.getLogger(__name__)


class GithubRepoMetadataRepository(IMetaDataRepository):
    def __init__(self, config: GithubRepoConfig):
        self.__gh = Github(config.access_token)
        self.__repo = self.__gh.get_repo(config.repo)
        self.__commit = config.commit

    async def save(self, metadata: TGFSMetadata) -> None:
        pass

    async def get(self) -> TGFSMetadata:
        root_dir = self._build_directory_structure()
        return TGFSMetadata(dir=root_dir)

    def _build_directory_structure(self) -> TGFSDirectory:
        root = TGFSDirectory.root_dir()

        try:
            contents = self.__repo.get_contents("", ref=self.__commit)
            self._process_contents(contents, root)
        except Exception as ex:
            logger.error(ex)

        return root

    def _process_contents(
        self, contents: list[ContentFile] | ContentFile, parent_dir: TGFSDirectory
    ) -> None:
        if not isinstance(contents, list):
            contents = [contents]

        for content in contents:
            if content.type == "dir":
                child_dir = parent_dir.create_dir(content.name, None)
                try:
                    child_contents = self.__repo.get_contents(
                        content.path, ref=self.__commit
                    )
                    self._process_contents(child_contents, child_dir)
                except Exception as ex:
                    logger.warning(
                        f"Failed to construct directory {content.name}: {ex}"
                    )
            elif content.type == "file":
                try:
                    file_name, message_id = content.name.rsplit(".", 1)
                    parent_dir.create_file_ref(file_name, int(message_id))
                except ValueError:
                    logger.warning(
                        f"Invalid name format for {content.name}, expected a format like 'name.message_id'"
                    )
