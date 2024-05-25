import { MessageNotFound } from 'src/errors/telegram';
import { TGFSFileRef } from 'src/model/directory';
import { TGFSFile, TGFSFileVersion } from 'src/model/file';
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
    const fd = new TGFSFile(fileMsg.name);

    if ('empty' in fileMsg) {
      fd.addEmptyVersion();
    } else {
      const sentFileMsg = await this.sendFile(fileMsg);
      fd.addVersionFromSentFileMessage(sentFileMsg);
    }

    return await this.sendFileDesc(fd);
  }

  public async getFileDesc(fileRef: TGFSFileRef): Promise<TGFSFile> {
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

    const versions = Object.values(fileDesc.versions);

    const nonEmptyVersions = versions.filter(
      (version) => version.messageId != TGFSFileVersion.EMPTY_FILE,
    ); // may contain empty versions

    const versionsWithoutSizeInfo = nonEmptyVersions.filter(
      (version) => version.size == TGFSFileVersion.INVALID_FILE_SIZE,
    );

    const fileMessages = await this.getMessages(
      versionsWithoutSizeInfo.map((version) => version.messageId),
    );

    versionsWithoutSizeInfo.forEach((version, i) => {
      const fileMessage = fileMessages[i];
      if (fileMessage) {
        version.size = Number(fileMessage.document.size);
      } else {
        version.setInvalid();
      }
    });

    if (versionsWithoutSizeInfo.length > 0) {
      await this.updateFileDesc(fileRef.getMessageId(), fileDesc);
    }

    return fileDesc;
  }

  public async addFileVersion(
    fr: TGFSFileRef,
    fileMsg: GeneralFileMessage,
  ): Promise<number> {
    const fd = await this.getFileDesc(fr);

    if (isFileMessageEmpty(fileMsg)) {
      fd.addEmptyVersion();
    } else {
      const sentFileMsg = await this.sendFile(fileMsg);
      fd.addVersionFromSentFileMessage(sentFileMsg);
    }
    return await this.sendFileDesc(fd, fr.getMessageId());
  }

  public async updateFileDesc(
    messageId: number,
    fileDesc: TGFSFile,
  ): Promise<number> {
    return await this.editMessageText(
      messageId,
      JSON.stringify(fileDesc.toObject()),
    );
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
      const sentFileMsg = await this.sendFile(fileMsg);
      const fv = fd.getVersion(versionId);
      fv.messageId = sentFileMsg.messageId;
      fv.size = sentFileMsg.size.toJSNumber();
      fd.updateVersion(fv);
    }
    return await this.sendFileDesc(fd, fr.getMessageId());
  }

  public async deleteFileVersion(
    fr: TGFSFileRef,
    versionId: string,
  ): Promise<number> {
    const fd = await this.getFileDesc(fr);
    fd.deleteVersion(versionId);
    return await this.sendFileDesc(fd, fr.getMessageId());
  }
}
