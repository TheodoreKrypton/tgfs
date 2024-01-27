import { TelegramClient } from 'telegram';

import { Telegram } from 'telegraf';

import { TGFSFileRef } from 'src/model/directory';
import { TGFSFile } from 'src/model/file';

import { MessageApi } from './message-api';

export class FileDescApi extends MessageApi {
  constructor(
    protected readonly account: TelegramClient,
    protected readonly bot: Telegram,
  ) {
    super(account, bot);
  }

  public async createFileDesc(
    name: string,
    fileContent?: string | Buffer,
  ): Promise<number> {
    const tgfsFile = new TGFSFile(name);

    if (fileContent) {
      const id = await this.sendFile(fileContent);
      tgfsFile.addVersionFromFileMessageId(id);
    } else {
      tgfsFile.addEmptyVersion();
    }

    return await this.sendMessage(JSON.stringify(tgfsFile.toObject()));
  }

  public async getFileDesc(
    fileRef: TGFSFileRef,
    withVersionInfo: boolean = true,
  ): Promise<TGFSFile> {
    const message = (await this.getMessagesByIds([fileRef.getMessageId()]))[0];

    const fileDesc = TGFSFile.fromObject(JSON.parse(message.text));

    if (withVersionInfo) {
      const versions = Object.values(fileDesc.versions);

      const nonEmptyVersions = versions.filter(
        (version) => version.messageId > 0,
      ); // may contain empty versions

      const fileMessages = await this.getMessagesByIds(
        nonEmptyVersions.map((version) => version.messageId),
      );

      nonEmptyVersions.forEach((version, i) => {
        const fileMessage = fileMessages[i];
        if (fileMessage) {
          version.size = Number(fileMessage.document.size);
        } else {
          version.setInvalid();
        }
      });
    }

    return fileDesc;
  }

  public async updateFileDesc(fr: TGFSFileRef, fd: TGFSFile): Promise<number> {
    return await this.editMessageText(
      fr.getMessageId(),
      JSON.stringify(fd.toObject()),
    );
  }
}
