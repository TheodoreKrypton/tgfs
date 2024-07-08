import { Hash, createHash } from 'crypto';
import fs from 'fs';

import bigInt from 'big-integer';

import { MessageApi } from 'src/api/client/message-api';
import {
  FileMessageEmpty,
  FileMessageFromBuffer,
  FileMessageFromPath,
  GeneralFileMessage,
  isFileMessageEmpty,
} from 'src/api/client/model';
import { SentFileMessage } from 'src/api/types';
import { TechnicalError } from 'src/errors/base';
import { TGFSFileVersion } from 'src/model/file';
import { manager } from 'src/server/manager';
import { Logger } from 'src/utils/logger';

import { createUploader } from './file-uploader';

export class FileRepository {
  constructor(private readonly msgApi: MessageApi) {}

  private async sha256(
    fileMsg: FileMessageFromPath | FileMessageFromBuffer | FileMessageEmpty,
  ): Promise<Hash> {
    if (isFileMessageEmpty(fileMsg)) {
      throw new TechnicalError('File is empty');
    }
    if ('path' in fileMsg) {
      return new Promise((resolve) => {
        const rs = fs.createReadStream(fileMsg.path);
        const hash = createHash('sha256');
        rs.on('end', () => {
          hash.end();
          resolve(hash);
        });
        rs.pipe(hash);
      });
    } else if ('buffer' in fileMsg) {
      return createHash('sha256').update(fileMsg.buffer);
    } else {
      throw new TechnicalError('File format is illegal');
    }
  }

  private static getFileCaption(fileMsg: GeneralFileMessage): string {
    let caption = fileMsg.caption ? `${fileMsg.caption}\n` : '';
    if (fileMsg.tags) {
      if (fileMsg.tags.sha256) {
        caption += `#sha256IS${fileMsg.tags.sha256}`;
      }
    }
    return caption;
  }

  private static report(
    uploaded: bigInt.BigInteger,
    totalSize: bigInt.BigInteger,
  ) {
    // Logger.info(`${(uploaded / totalSize) * 100}% uploaded`);
  }

  private async sendFile(
    fileMsg: GeneralFileMessage,
  ): Promise<SentFileMessage> {
    let messageId = TGFSFileVersion.EMPTY_FILE;
    const uploader = createUploader(this.msgApi.tdlib, fileMsg, async () => {
      messageId = (
        await uploader.send(
          this.msgApi.privateChannelId,
          FileRepository.getFileCaption(fileMsg),
        )
      ).messageId;
    });
    const size = await uploader.upload(
      fileMsg,
      FileRepository.report,
      fileMsg.name,
    );

    Logger.debug('File sent', JSON.stringify(fileMsg));

    return {
      messageId,
      size,
    };
  }

  public async save(fileMsg: GeneralFileMessage): Promise<SentFileMessage> {
    if ('stream' in fileMsg) {
      // Unable to calculate sha256 for file as a stream. So just send it.
      Logger.debug(
        `Sending file ${JSON.stringify({ ...fileMsg, stream: 'hidden' })}`,
      );
      return await this.sendFile(fileMsg);
    }

    Logger.debug(`Sending file ${JSON.stringify(fileMsg)}`);

    const fileHash = (await this.sha256(fileMsg)).digest('hex');

    fileMsg.tags = { sha256: fileHash };

    const existingFileMsg = await this.msgApi.searchMessages(
      `#sha256IS${fileHash}`,
    );

    if (existingFileMsg.length > 0) {
      const msg = existingFileMsg[0];
      Logger.debug(
        `Found file with the same sha256 ${fileHash}, skip uploading`,
        JSON.stringify(msg),
      );
      return {
        messageId: msg.messageId,
        size: msg.document.size,
      };
    }

    return await this.sendFile(fileMsg);
  }

  public async update(
    messageId: number,
    buffer: Buffer,
    name: string,
    caption: string,
  ): Promise<number> {
    const fileMsg: FileMessageFromBuffer = {
      buffer,
      name,
      caption,
    };
    const uploader = createUploader(this.msgApi.tdlib, fileMsg, async () => {
      await this.msgApi.tdlib.bot.editMessageMedia({
        chatId: this.msgApi.privateChannelId,
        messageId,
        file: uploader.getUploadedFile(),
      });
    });
    await uploader.upload(fileMsg, FileRepository.report, fileMsg.name);
    return messageId;
  }

  public async *downloadFile(
    name: string,
    messageId: number,
  ): AsyncGenerator<Buffer> {
    let downloaded: bigInt.BigInteger = bigInt.zero;

    const { chunks, size } = await this.msgApi.downloadFile(messageId);

    const task = manager.createDownloadTask(name, size);
    task.begin();

    try {
      for await (const buffer of chunks) {
        yield buffer;
        downloaded = downloaded.add(buffer.length);
        task.reportProgress(downloaded);
      }
    } catch (err) {
      task.setErrors([err]);
      throw err;
    } finally {
      task.complete();
    }
  }
}
