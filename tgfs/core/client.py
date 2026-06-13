from typing import Dict, Optional

from tgfs.config import EncryptionConfig, MetadataConfig, MetadataType
from tgfs.core.api import DirectoryApi, FileApi, FileDescApi, MessageApi, MetaDataApi
from tgfs.core.repository.impl import (
    TGMsgFDRepository,
    TGMsgFileContentRepository,
    TGMsgMetadataRepository,
)
from tgfs.core.repository.interface import (
    IFileContentRepository,
    IMetaDataRepository,
)
from tgfs.telegram import TDLibApi


class Client:
    def __init__(
        self,
        name: str,
        message_api: MessageApi,
        file_api: FileApi,
        dir_api: DirectoryApi,
        fc_repo: IFileContentRepository,
    ):
        self.name = name
        self.message_api = message_api
        self.file_api = file_api
        self.dir_api = dir_api
        self.fc_repo = fc_repo

    @classmethod
    async def create(
        cls,
        channel_id: str,
        metadata_cfg: MetadataConfig,
        tdlib_api: TDLibApi,
        use_account_api_to_upload: bool = False,
        encryption_cfg: Optional[EncryptionConfig] = None,
    ) -> "Client":
        channel = await tdlib_api.next_bot.resolve_channel_id(channel_id)
        message_api = MessageApi(tdlib_api, channel)

        fc_repo: IFileContentRepository = TGMsgFileContentRepository(
            message_api,
            use_account_api_to_upload
            and tdlib_api.account is not None
            and (await tdlib_api.account.get_me()).is_premium,
        )

        # Wrap the file-content repository in an encryption decorator if
        # encryption is enabled in the config. Everything downstream
        # (FileApi, WebDAV, etc.) is unchanged: the wrapper preserves the
        # IFileContentRepository contract.
        if encryption_cfg is not None and encryption_cfg.enabled:
            from tgfs.crypto.bootstrap import load_master_key
            from tgfs.crypto.repository import EncryptingFileContentRepository

            master = load_master_key(encryption_cfg)
            fc_repo = EncryptingFileContentRepository(
                fc_repo,
                master_key=master.key,
                chunk_size=encryption_cfg.chunk_size,
            )

        fd_repo = TGMsgFDRepository(message_api)

        if metadata_cfg.type == MetadataType.PINNED_MESSAGE:
            metadata_repo: IMetaDataRepository = TGMsgMetadataRepository(
                message_api, fc_repo
            )
        else:
            if (github_repo_config := metadata_cfg.github_repo) is None:
                raise ValueError(
                    "configuration tgfs -> metadata -> github is required."
                )
            from tgfs.core.repository.impl.metadata.github_repo import (
                GithubRepoMetadataRepository,
            )

            metadata_repo = GithubRepoMetadataRepository(github_repo_config)

        fd_api = FileDescApi(fd_repo, fc_repo)

        metadata_api = MetaDataApi(metadata_repo)
        await metadata_api.init()

        file_api = FileApi(metadata_api, fd_api)
        dir_api = DirectoryApi(metadata_api)

        return cls(
            name=metadata_cfg.name,
            message_api=message_api,
            file_api=file_api,
            dir_api=dir_api,
            fc_repo=fc_repo,
        )


Clients = Dict[str, Client]
