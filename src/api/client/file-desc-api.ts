import { Api, TelegramClient } from 'telegram';
import { FileLike } from 'telegram/define';

import { TGFSFileRef } from 'src/model/directory';
import { TGFSFile } from 'src/model/file';

import { MessageApi } from './message-api';

export class FileDescApi extends MessageApi {
  constructor(protected readonly client: TelegramClient) {
    super(client);
  }

  public async createFileDesc(
    name: string,
    fileContent?: FileLike,
  ): Promise<Api.Message> {
    const tgfsFile = new TGFSFile(name);

    if (fileContent) {
      const uploadFileMsg = await this.sendFile(fileContent);
      tgfsFile.addVersionFromFileMessage(uploadFileMsg);
    } else {
      tgfsFile.addEmptyVersion();
    }

    return await this.sendMessage(JSON.stringify(tgfsFile.toObject()));
  }

  public async getFileDesc(
    fileRef: TGFSFileRef,
    withVersionInfo: boolean = true,
  ): Promise<TGFSFile> {
    const message = (await this.getMessages([fileRef.getMessageId()]))[0];
    const fileDesc = TGFSFile.fromObject(JSON.parse(message.text));

    if (withVersionInfo) {
      const versions = Object.values(fileDesc.versions);

      const nonEmptyVersions = versions.filter(
        (version) => version.messageId > 0,
      ); // may contain empty versions

      const fileMessages = await this.getMessages(
        nonEmptyVersions.map((version) => version.messageId),
      );

      nonEmptyVersions.forEach((version, i) => {
        const fileMessage = fileMessages[i];
        version.size = Number(fileMessage.document.size);
      });
    }

    return fileDesc;
  }

  public async updateFileDesc(fr: TGFSFileRef, fd: TGFSFile) {
    return await this.editMessage(fr.getMessageId(), {
      text: JSON.stringify(fd.toObject()),
    });
  }
}
