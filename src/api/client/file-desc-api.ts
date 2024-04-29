import { MessageNotFound } from 'src/errors/telegram';
import { TGFSFileRef } from 'src/model/directory';
import { TGFSFile } from 'src/model/file';
import { Logger } from 'src/utils/logger';

import { MessageApi } from './message-api';
import { GeneralFileMessage, isFileMessageEmpty } from './message-api/types';

export class FileDescApi extends MessageApi {
  private async sendFileDesc(
    fd: TGFSFile,
    messageId?: number,
  ): Promise<number> {
    Logger.debug(
      `sendFileDesc ${JSON.stringify(fd.toObject())}, messageId=${messageId}`,
    );
    if (!messageId) {
      return await this.sendText(JSON.stringify(fd.toObject()));
    }
    // edit an existing message
    try {
      return await this.editMessageText(
        messageId,
        JSON.stringify(fd.toObject()),
      );
    } catch (err) {
      if (err instanceof MessageNotFound) {
        // the message to edit is gone
        return await this.sendText(JSON.stringify(fd.toObject()));
      } else {
        throw err;
      }
    }
  }

  public async createFileDesc(fileMsg: GeneralFileMessage): Promise<number> {
    const tgfsFile = new TGFSFile(fileMsg.name);

    if ('empty' in fileMsg) {
      tgfsFile.addEmptyVersion();
    } else {
      const id = await this.sendFile(fileMsg);
      tgfsFile.addVersionFromFileMessageId(id);
    }

    return await this.sendFileDesc(tgfsFile);
  }

  public async getFileDesc(
    fileRef: TGFSFileRef,
    withVersionInfo: boolean = true,
  ): Promise<TGFSFile> {
    const message = (await this.getMessages([fileRef.getMessageId()]))[0];

    if (!message) {
      Logger.error(
        `File description (messageId: ${fileRef.getMessageId()}) for ${
          fileRef.name
        } not found`,
      );
      return TGFSFile.empty(`[Content Not Found]${fileRef.name}`);
    }

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
        if (fileMessage) {
          version.size = Number(fileMessage.document.size);
        } else {
          version.setInvalid();
        }
      });
    }

    return fileDesc;
  }

  public async addFileVersion(
    fr: TGFSFileRef,
    fileMsg: GeneralFileMessage,
  ): Promise<number> {
    const fd = await this.getFileDesc(fr, false);

    if (isFileMessageEmpty(fileMsg)) {
      fd.addEmptyVersion();
    } else {
      const messageId = await this.sendFile(fileMsg);
      fd.addVersionFromFileMessageId(messageId);
    }
    return await this.sendFileDesc(fd, fr.getMessageId());
  }

  public async updateFileVersion(
    fr: TGFSFileRef,
    fileMsg: GeneralFileMessage,
    versionId: string,
  ): Promise<number> {
    const fd = await this.getFileDesc(fr);
    if (isFileMessageEmpty(fileMsg)) {
      const fv = fd.getVersion(versionId);
      fv.setInvalid();
      fd.updateVersion(fv);
    } else {
      const messageId = await this.sendFile(fileMsg);
      const fv = fd.getVersion(versionId);
      fv.messageId = messageId;
      fd.updateVersion(fv);
    }
    return await this.sendFileDesc(fd, fr.getMessageId());
  }

  public async deleteFileVersion(
    fr: TGFSFileRef,
    versionId: string,
  ): Promise<number> {
    const fd = await this.getFileDesc(fr, false);
    fd.deleteVersion(versionId);
    return await this.sendFileDesc(fd, fr.getMessageId());
  }
}
