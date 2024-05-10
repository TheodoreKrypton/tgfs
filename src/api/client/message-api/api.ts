import { Hash, createHash } from 'crypto';
import fs from 'fs';

import bigInt from 'big-integer';

import { IBot, TDLibApi } from 'src/api/interface';
import { config } from 'src/config';
import { TechnicalError } from 'src/errors/base';
import { MessageNotFound } from 'src/errors/telegram';
import { TGFSFileVersion } from 'src/model/file';
import { manager } from 'src/server/manager';
import { Logger } from 'src/utils/logger';

import { getUploader } from './file-uploader';
import { MessageBroker } from './message-broker';
import {
  FileMessageEmpty,
  FileMessageFromBuffer,
  FileMessageFromPath,
  GeneralFileMessage,
  isFileMessageEmpty,
} from './types';

export class MessageApi extends MessageBroker {
  constructor(
    protected readonly tdlib: TDLibApi,
    protected readonly bot: IBot,
  ) {
    super(tdlib);
  }

  protected async sendText(message: string): Promise<number> {
    return (
      await this.tdlib.bot.sendText({
        chatId: this.privateChannelId,
        text: message,
      })
    ).messageId;
  }

  protected async editMessageText(
    messageId: number,
    message: string,
  ): Promise<number> {
    try {
      return (
        await this.tdlib.bot.editMessageText({
          chatId: this.privateChannelId,
          messageId,
          text: message,
        })
      ).messageId;
    } catch (err) {
      if (err.message === 'message to edit not found') {
        throw new MessageNotFound(messageId);
      } else {
        throw err;
      }
    }
  }

  protected async editMessageMedia(
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
    const uploader = getUploader(this.tdlib, fileMsg, async () => {
      await this.tdlib.bot.editMessageMedia({
        chatId: this.privateChannelId,
        messageId,
        file: uploader.getUploadedFile(),
      });
    });
    await uploader.upload(fileMsg, MessageApi.report, fileMsg.name);
    return messageId;
  }

  protected async pinMessage(messageId: number) {
    return await this.tdlib.bot.pinMessage({
      chatId: this.privateChannelId,
      messageId,
    });
  }

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

  private async _sendFile(fileMsg: GeneralFileMessage): Promise<number> {
    let messageId = TGFSFileVersion.EMPTY_FILE;
    const uploader = getUploader(this.tdlib, fileMsg, async () => {
      messageId = (
        await uploader.send(
          this.privateChannelId,
          MessageApi.getFileCaption(fileMsg),
        )
      ).messageId;
    });
    await uploader.upload(fileMsg, MessageApi.report, fileMsg.name);

    Logger.debug('File sent', JSON.stringify(fileMsg));
    return messageId;
  }

  protected async sendFile(fileMsg: GeneralFileMessage): Promise<number> {
    if ('stream' in fileMsg) {
      // Unable to calculate sha256 for file as a stream. So just send it.
      Logger.debug(
        `Sending file ${JSON.stringify({ ...fileMsg, stream: 'hidden' })}`,
      );
      return await this._sendFile(fileMsg);
    }

    Logger.debug(`Sending file ${JSON.stringify(fileMsg)}`);

    const fileHash = (await this.sha256(fileMsg)).digest('hex');

    fileMsg.tags = { sha256: fileHash };

    const existingFile = await this.tdlib.account.searchMessages({
      chatId: this.privateChannelId,
      search: `#sha256IS${fileHash}`,
    });

    if (existingFile.length > 0) {
      Logger.debug(
        `Found file with the same sha256 ${fileHash}, skip uploading`,
        JSON.stringify(existingFile[0]),
      );
      return existingFile[0].messageId;
    }

    return await this._sendFile(fileMsg);
  }

  protected async *downloadFile(
    name: string,
    messageId: number,
  ): AsyncGenerator<Buffer> {
    let downloaded: bigInt.BigInteger = bigInt.zero;

    const { chunks, size } = await this.tdlib.account.downloadFile({
      chatId: this.privateChannelId,
      messageId: messageId,
      chunkSize: config.tgfs.download.chunk_size_kb,
    });

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
