import { Hash, createHash } from 'crypto';
import fs from 'fs';

import { Api } from 'telegram';

import bigInt from 'big-integer';
import path from 'path';

import { IBotApi, ITDLibApi } from 'src/api/interface';
import { BigFile } from 'src/api/types';
import { generateFileId, getAppropriatedPartSize } from 'src/api/utils';
import { config } from 'src/config';
import { TechnicalError } from 'src/errors/base';
import { db } from 'src/server/manager/db';

class MessageBroker {
  public readonly privateChannelId = Number(
    config.telegram.private_file_channel,
  );

  constructor(
    protected readonly tdlib: ITDLibApi,
    protected requests: Array<{
      ids: number[];
      resolve: (result: unknown) => void;
      reject: (error: unknown) => void;
    }> = [],
    protected timeout: NodeJS.Timeout = null,
  ) {}

  async getMessages(ids: number[]): Promise<Api.Message[]> {
    return new Promise((resolve, reject) => {
      this.requests.push({ ids, resolve, reject });
      if (this.timeout) {
        clearTimeout(this.timeout);
      }
      this.timeout = setTimeout(async () => {
        let requests = [];
        [requests, this.requests] = [[...this.requests], []];
        const ids = [...new Set(requests.map((item) => item.ids).flat())];

        try {
          const messages = await this.tdlib.getMessages({
            chatId: this.privateChannelId,
            messageIds: ids,
          });
          const messageMap = new Map();
          messages.forEach((message) => {
            if (message) {
              messageMap.set(message.messageId, message);
            }
          });
          requests.forEach((request) => {
            const result = request.ids.map((id: number) => messageMap.get(id));
            request.resolve(result);
          });
        } catch (err) {
          requests.forEach((request) => {
            request.reject(err);
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

  constructor(private readonly tdlib: ITDLibApi) {
    this.fileId = generateFileId();
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
        // console.log(this.partCnt);
        const rsp = await this.tdlib.saveBigFilePart({
          fileId: this.fileId,
          filePart: this.partCnt,
          fileTotalParts: this.parts,
          bytes: buffer,
        });
        // console.log(rsp);
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

    const createWorker = async (workerId: number): Promise<void> => {
      while (!this.done()) {
        await this.uploadNextPart();
        if (callback) {
          callback(this.uploaded);
        }
      }
    };

    const promises: Array<Promise<void>> = [];
    for (let i = 0; i < workers; i++) {
      promises.push(createWorker(i));
    }

    await Promise.all(promises);

    this.close();
  }

  public done(): boolean {
    return this.uploaded >= this.fileSize;
  }

  public getUploadedFile(): BigFile {
    return {
      id: this.fileId,
      parts: this.parts,
      name: this.fileName,
    };
  }
}

export class MessageApi extends MessageBroker {
  constructor(
    protected readonly tdlib: ITDLibApi,
    protected readonly bot: IBotApi,
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

  protected async editMessageMedia(messageId: number, media: Buffer) {
    return await this.bot.editMessageMedia({
      chatId: this.privateChannelId,
      messageId,
      buffer: media,
    });
  }

  protected async pinMessage(messageId: number) {
    return await this.bot.pinMessage({
      chatId: this.privateChannelId,
      messageId,
    });
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

    const uploader = new FileUploader(this.tdlib);
    await uploader.upload(filePath, WORKERS, (uploaded) => {
      // console.log(uploaded);
    });
    const file = uploader.getUploadedFile();

    return await this.tdlib.sendBigFile({
      chatId: this.privateChannelId,
      file,
    });
  }

  private async sendBigFileFromBuffer(buffer: Buffer) {
    return await this.tdlib.sendFileFromBuffer({
      chatId: this.privateChannelId,
      buffer,
    });
  }

  private async sendBigFile(file: string | Buffer) {
    return await (typeof file === 'string'
      ? this.sendBigFileFromPath(file)
      : this.sendBigFileFromBuffer(file));
  }

  private async sendSmallFileFromPath(filePath: string) {
    return await this.bot.sendFileFromPath({
      chatId: this.privateChannelId,
      name: path.basename(filePath),
      filePath,
    });
  }

  private async sendSmallFileFromBuffer(buffer: Buffer) {
    return await this.bot.sendFileFromBuffer({
      chatId: this.privateChannelId,
      name: 'unnamed',
      buffer,
    });
  }

  private async sendSmallFile(file: string | Buffer) {
    return await (typeof file === 'string'
      ? this.sendSmallFileFromPath(file)
      : this.sendSmallFileFromBuffer(file));
  }

  protected async sendFile(file: string | Buffer): Promise<number> {
    const fileHash = (await this.sha256(file)).digest('hex');

    const existingFile = await this.tdlib.searchMessages({
      chatId: this.privateChannelId,
      search: `#sha256IS${fileHash}`,
    });

    if (existingFile.length > 0) {
      return existingFile[0].messageId;
    }

    const fileSize =
      typeof file === 'string' ? fs.statSync(file).size : file.length;

    if (fileSize < 50 * 1024 * 1024) {
      return (await this.sendSmallFile(file)).messageId;
    } else {
      return (await this.sendBigFile(file)).messageId;
    }
  }

  protected async *downloadFile(
    name: string,
    messageId: number,
  ): AsyncGenerator<Buffer> {
    const task = db.createTask(name, 0, 'download');

    let downloaded = 0;

    for await (const buffer of this.tdlib.downloadFile({
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
