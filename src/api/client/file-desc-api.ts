import { MessageNotFound } from 'src/errors/telegram';
import { TGFSFileRef } from 'src/model/directory';
import { TGFSFile, TGFSFileVersion } from 'src/model/file';
import { Logger } from 'src/utils/logger';

import { MessageApi } from './message-api';
import { GeneralFileMessage, isFileMessageEmpty } from './message-api/types';

type FileDescAPIResponse = {
  messageId?: number;
  fd?: TGFSFile;
};

export class FileDescApi extends MessageApi {
  private async sendFileDesc(
    fd: TGFSFile,
    messageId?: number,
  ): Promise<FileDescAPIResponse> {
    if (!messageId) {
      return {
        messageId: await this.sendText(JSON.stringify(fd.toObject())),
        fd,
      };
    }
    // edit an existing message
    try {
      return {
        messageId: await this.editMessageText(
          messageId,
          JSON.stringify(fd.toObject()),
        ),
        fd,
      };
    } catch (err) {
      if (err instanceof MessageNotFound) {
        // the message to edit is gone
        return {
          messageId: await this.sendText(JSON.stringify(fd.toObject())),
          fd,
        };
      } else {
        throw err;
      }
    }
  }

  public async createFileDesc(
    fileMsg: GeneralFileMessage,
  ): Promise<FileDescAPIResponse> {
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
      const { fd } = await this.updateFileDesc(
        fileRef.getMessageId(),
        fileDesc,
      );
      return fd;
    }

    return fileDesc;
  }

  public async addFileVersion(
    fr: TGFSFileRef,
    fileMsg: GeneralFileMessage,
  ): Promise<FileDescAPIResponse> {
    const fd = await this.getFileDesc(fr);

    if (isFileMessageEmpty(fileMsg)) {
      fd.addEmptyVersion();
    } else {
      const sentFileMsg = await this.sendFile(fileMsg);
      fd.addVersionFromSentFileMessage(sentFileMsg);
    }
    await this.sendFileDesc(fd, fr.getMessageId());
    return { messageId: fr.getMessageId(), fd };
  }

  public async updateFileDesc(
    messageId: number,
    fileDesc: TGFSFile,
  ): Promise<FileDescAPIResponse> {
    return {
      messageId: await this.editMessageText(
        messageId,
        JSON.stringify(fileDesc.toObject()),
      ),
      fd: fileDesc,
    };
  }

  public async updateFileVersion(
    fr: TGFSFileRef,
    fileMsg: GeneralFileMessage,
    versionId: string,
  ): Promise<FileDescAPIResponse> {
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
    await this.sendFileDesc(fd, fr.getMessageId());
    return { messageId: fr.getMessageId(), fd };
  }

  public async deleteFileVersion(
    fr: TGFSFileRef,
    versionId: string,
  ): Promise<FileDescAPIResponse> {
    const fd = await this.getFileDesc(fr);
    fd.deleteVersion(versionId);
    await this.sendFileDesc(fd, fr.getMessageId());
    return { messageId: fr.getMessageId(), fd };
  }
}
