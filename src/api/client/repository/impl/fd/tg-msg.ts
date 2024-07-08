import { MessageApi } from 'src/api/client/message-api';
import { FileDescAPIResponse } from 'src/api/client/model';
import { IFDRepository } from 'src/api/client/repository/interface';
import { MessageNotFound } from 'src/errors/telegram';
import { TGFSFileRef } from 'src/model/directory';
import { TGFSFile, TGFSFileVersion } from 'src/model/file';
import { Logger } from 'src/utils/logger';

export class TGMsgFDRepository implements IFDRepository {
  constructor(private readonly msgApi: MessageApi) {}

  public async save(
    fd: TGFSFile,
    messageId?: number,
  ): Promise<FileDescAPIResponse> {
    if (!messageId) {
      return {
        messageId: await this.msgApi.sendText(JSON.stringify(fd.toObject())),
        fd,
      };
    }
    // edit an existing message
    try {
      return await this.update(messageId, fd);
    } catch (err) {
      if (err instanceof MessageNotFound) {
        // the message to edit is gone
        return this.save(fd);
      } else {
        throw err;
      }
    }
  }

  private async update(
    messageId: number,
    fd: TGFSFile,
  ): Promise<FileDescAPIResponse> {
    return {
      messageId: await this.msgApi.editMessageText(
        messageId,
        JSON.stringify(fd.toObject()),
      ),
      fd,
    };
  }

  public async get(fileRef: TGFSFileRef): Promise<TGFSFile> {
    const message = (
      await this.msgApi.getMessages([fileRef.getMessageId()])
    )[0];

    if (!message) {
      Logger.error(
        `File description (messageId: ${fileRef.getMessageId()}) for ${
          fileRef.name
        } not found`,
      );
      return TGFSFile.empty(`[Content Not Found]${fileRef.name}`);
    }

    const fd = TGFSFile.fromObject(JSON.parse(message.text));

    const versions = Object.values(fd.versions);

    const nonEmptyVersions = versions.filter(
      (version) => version.messageId != TGFSFileVersion.EMPTY_FILE,
    ); // may contain empty versions

    const versionsWithoutSizeInfo = nonEmptyVersions.filter(
      (version) => version.size == TGFSFileVersion.INVALID_FILE_SIZE,
    );

    const fileMessages = await this.msgApi.getMessages(
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
      return (await this.update(fileRef.getMessageId(), fd)).fd;
    }

    return fd;
  }
}
