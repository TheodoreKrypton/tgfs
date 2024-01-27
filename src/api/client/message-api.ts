import { Hash, createHash } from 'crypto';
import fs from 'fs';

import { Api, TelegramClient } from 'telegram';
import { generateRandomBytes, readBigIntFromBuffer } from 'telegram/Helpers.js';
import { getAppropriatedPartSize } from 'telegram/Utils';
import { IterDownloadFunction } from 'telegram/client/downloads';
import { IterMessagesParams } from 'telegram/client/messages';

import { Telegram } from 'telegraf';

import bigInt from 'big-integer';
import path from 'path';

import { config } from 'src/config';
import { TechnicalError } from 'src/errors/base';
import { db } from 'src/server/manager/db';

class MessageBroker {
  public readonly privateChannelId = config.telegram.private_file_channel;

  constructor(
    protected readonly account: TelegramClient,
    protected buffer: Array<{
      ids: number[];
      resolve: (result: unknown) => void;
      reject: (error: unknown) => void;
    }> = [],
    protected timeout: NodeJS.Timeout = null,
  ) {}

  async getMessagesByIds(ids: number[]) {
    return new Promise((resolve, reject) => {
      this.buffer.push({ ids, resolve, reject });
      if (this.timeout) {
        clearTimeout(this.timeout);
      }
      this.timeout = setTimeout(async () => {
        let buffer = [];
        [buffer, this.buffer] = [[...this.buffer], []];
        const ids = [...new Set(buffer.map((item) => item.ids).flat())];

        try {
          const messages = await this.account.getMessages(
            this.privateChannelId,
            {
              ids,
            },
          );
          const messageMap = new Map();
          messages.forEach((message) => {
            if (message) {
              messageMap.set(message.id, message);
            }
          });
          buffer.forEach((item) => {
            const result = item.ids.map((id: number) => messageMap.get(id));
            item.resolve(result);
          });
        } catch (err) {
          buffer.forEach((item) => {
            item.reject(err);
          });
        }
      }, 100);
    });
  }
}

export class FileUploader {
  fileId: bigInt.BigInteger;
  fileName: string;
  fileSize: number;
  chunkSize: number;
  parts: number;
  file: number;

  partCnt: number = -1;
  uploaded: number = 0;

  constructor(private readonly client: TelegramClient) {
    this.fileId = FileUploader.generateFileId();
  }

  private static generateFileId() {
    return readBigIntFromBuffer(generateRandomBytes(8), true, true);
  }

  public open(filePath: string) {
    this.fileName = path.basename(filePath);
    this.fileSize = fs.statSync(filePath).size;
    this.chunkSize = getAppropriatedPartSize(bigInt(this.fileSize)) * 1024;
    this.parts = Math.ceil(this.fileSize / this.chunkSize);
    this.file = fs.openSync(filePath, 'r');
  }

  public close() {
    fs.closeSync(this.file);
  }

  public async uploadNextPart(): Promise<number> {
    const chunkLength =
      this.uploaded + this.chunkSize > this.fileSize
        ? this.fileSize - this.uploaded
        : this.chunkSize;

    const buffer = Buffer.alloc(chunkLength);

    fs.readSync(this.file, buffer, {
      position: this.uploaded,
      length: chunkLength,
    });

    this.uploaded += chunkLength;
    this.partCnt += 1;

    let retry = 3;
    while (retry) {
      try {
        await this.client.invoke(
          new Api.upload.SaveBigFilePart({
            fileId: this.fileId,
            filePart: this.partCnt,
            fileTotalParts: this.parts,
            bytes: buffer,
          }),
        );
        return chunkLength;
      } catch (err) {
        console.error(err);
        retry -= 1;
        if (retry === 0) {
          throw err;
        }
      }
    }
  }

  public async upload(
    filePath: string,
    workers: number = 15,
    callback?: (uploaded: number) => void,
  ) {
    this.open(filePath);

    const promises: Array<Promise<void>> = [];
    for (let i = 0; i < workers; i++) {
      promises.push(
        new Promise((resolve, reject) => {
          while (!this.done()) {
            this.uploadNextPart()
              .then((uploaded) => {
                console.log(i, uploaded);
                if (callback) {
                  callback(uploaded);
                }
              })
              .catch((err) => {
                reject(err);
              });
          }
          resolve();
        }),
      );
    }

    console.log("Uploading file '" + this.fileName + "'...");

    await Promise.all(promises);

    this.close();
  }

  public done(): boolean {
    return this.uploaded >= this.fileSize;
  }

  public getUploadedFile() {
    return new Api.InputFileBig({
      id: this.fileId,
      parts: this.parts,
      name: this.fileName,
    });
  }
}

export class MessageApi extends MessageBroker {
  constructor(
    protected readonly account: TelegramClient,
    protected readonly bot: Telegram,
  ) {
    super(account);
  }

  protected async sendMessage(message: string): Promise<number> {
    return (await this.bot.sendMessage(this.privateChannelId, message))
      .message_id;
  }

  protected async getMessages(params: Partial<IterMessagesParams>) {
    return await this.account.getMessages(this.privateChannelId, params);
  }

  protected async editMessageText(
    messageId: number,
    message: string,
  ): Promise<number> {
    await this.bot.editMessageText(
      this.privateChannelId,
      messageId,
      undefined,
      message,
    );
    return messageId;
  }

  protected async editMessageMedia(messageId: number, media: Buffer) {
    if (typeof media === 'string') {
    } else {
      return await this.bot.editMessageMedia(
        this.privateChannelId,
        messageId,
        undefined,
        {
          type: 'document',
          media: {
            source: media,
          },
        },
      );
    }
  }

  protected async pinMessage(messageId: number) {
    return await this.bot.pinChatMessage(this.privateChannelId, messageId);
  }

  private async sha256(file: string | Buffer): Promise<Hash> {
    if (typeof file === 'string') {
      return new Promise((resolve) => {
        const rs = fs.createReadStream(file);
        const hash = createHash('sha256');
        rs.on('end', () => {
          hash.end();
          resolve(hash);
        });
        rs.pipe(hash);
      });
    } else if (file instanceof Buffer) {
      return createHash('sha256').update(file);
    } else {
      throw new TechnicalError('File format is illegal');
    }
  }

  private async sendBigFileFromPath(filePath: string) {
    const WORKERS = 15;

    const uploader = new FileUploader(this.account);
    await uploader.upload(filePath, WORKERS, (uploaded) => {
      console.log(uploaded);
    });
    const file = uploader.getUploadedFile();

    return await this.account.sendFile(this.privateChannelId, {
      file,
    });
  }

  private async sendBigFileAsBuffer(file: Buffer) {
    return await this.account.sendFile(this.privateChannelId, {
      file,
    });
  }

  private async sendBigFile(file: string | Buffer) {
    return await (typeof file === 'string'
      ? this.sendBigFileFromPath(file)
      : this.sendBigFileAsBuffer(file));
  }

  private async sendSmallFileFromPath(filePath: string) {
    return await this.bot.sendDocument(this.privateChannelId, {
      source: filePath,
      filename: path.basename(filePath),
    });
  }

  private async sendSmallFileAsBuffer(file: Buffer) {
    return await this.bot.sendDocument(this.privateChannelId, {
      source: file,
      filename: 'unnamed',
    });
  }

  private async sendSmallFile(file: string | Buffer) {
    return await (typeof file === 'string'
      ? this.sendSmallFileFromPath(file)
      : this.sendSmallFileAsBuffer(file));
  }

  protected async sendFile(file: string | Buffer): Promise<number> {
    const fileHash = (await this.sha256(file)).digest('hex');

    const existingFile = await this.getMessages({
      search: `#sha256IS${fileHash}`,
    });

    if (existingFile.length > 0) {
      return existingFile[0].id;
    }

    const fileSize =
      typeof file === 'string' ? fs.statSync(file).size : file.length;

    if (fileSize < 50 * 1024 * 1024) {
      return (await this.sendSmallFile(file)).message_id;
    } else {
      return (await this.sendBigFile(file)).id;
    }
  }

  protected async downloadFile(
    file: { name: string; messageId: number },
    options?: IterDownloadFunction,
  ) {
    const message = (await this.getMessagesByIds([file.messageId]))[0];

    const fileSize = Number(message.document.size);
    const chunkSize = config.tgfs.download.chunksize * 1024;

    const task = db.createTask(file.name, 0, 'download');

    const buffer = Buffer.alloc(fileSize);
    let i = 0;
    for await (const chunk of this.account.iterDownload({
      file: new Api.InputDocumentFileLocation({
        id: message.document.id,
        accessHash: message.document.accessHash,
        fileReference: message.document.fileReference,
        thumbSize: '',
      }),
      requestSize: chunkSize,
    })) {
      chunk.copy(buffer, i * chunkSize, 0, Number(chunk.length));
      i += 1;
      task.reportProgress(i * chunkSize);
    }

    task.finish();
    return buffer;
  }
}
