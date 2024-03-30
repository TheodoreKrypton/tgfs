import { Hash, createHash } from 'crypto';
import fs from 'fs';

import { IBot, TDLibApi } from 'src/api/interface';
import { config } from 'src/config';
import { TechnicalError } from 'src/errors/base';
import { db } from 'src/server/manager/db';

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
      await this.bot.sendText({
        chatId: this.privateChannelId,
        text: message,
      })
    ).messageId;
  }

  protected async editMessageText(
    messageId: number,
    message: string,
  ): Promise<number> {
    return (
      await this.bot.editMessageText({
        chatId: this.privateChannelId,
        messageId,
        text: message,
      })
    ).messageId;
  }

  protected async editMessageMedia(
    messageId: number,
    buffer: Buffer,
    name: string,
    caption: string,
  ): Promise<number> {
    return (
      await this.bot.editMessageMedia({
        chatId: this.privateChannelId,
        messageId,
        buffer,
        name,
        caption,
      })
    ).messageId;
  }

  protected async pinMessage(messageId: number) {
    return await this.bot.pinMessage({
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

  private static report(uploaded: number, totalSize: number) {
    // Logger.info(`${(uploaded / totalSize) * 100}% uploaded`);
  }

  protected async sendFile(fileMsg: GeneralFileMessage): Promise<number> {
    const _send = async (fileMsg: GeneralFileMessage): Promise<number> => {
      const uploader = getUploader(this.tdlib, fileMsg);
      await uploader.upload(fileMsg, MessageApi.report);
      return (
        await uploader.send(
          this.privateChannelId,
          MessageApi.getFileCaption(fileMsg),
        )
      ).messageId;
    };

    if ('stream' in fileMsg) {
      return await _send(fileMsg);
    }

    const fileHash = (await this.sha256(fileMsg))
      .digest('hex')
      .substring(0, 16);

    fileMsg.tags = { sha256: fileHash };

    const existingFile = await this.tdlib.account.searchMessages({
      chatId: this.privateChannelId,
      search: `#sha256IS${fileHash}`,
    });

    if (existingFile.length > 0) {
      return existingFile[0].messageId;
    }

    return await _send(fileMsg);
  }

  protected async *downloadFile(
    name: string,
    messageId: number,
  ): AsyncGenerator<Buffer> {
    const task = db.createTask(name, 0, 'download');

    let downloaded = 0;

    for await (const buffer of this.tdlib.account.downloadFile({
      chatId: this.privateChannelId,
      messageId: messageId,
      chunkSize: config.tgfs.download.chunk_size_kb,
    })) {
      yield buffer;
      downloaded += buffer.length;
      task.reportProgress(downloaded);
    }

    task.finish();
  }
}
