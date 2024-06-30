import fs from 'fs';
import { Readable } from 'stream';

import { RPCError } from 'telegram/errors';

import bigInt from 'big-integer';
import path from 'path';

import { ITDLibClient, TDLibApi } from 'src/api/interface';
import { SendMessageResp, UploadedFile } from 'src/api/types';
import { generateFileId, getAppropriatedPartSize } from 'src/api/utils';
import { AggregatedError } from 'src/errors/base';
import { FileTooBig } from 'src/errors/telegram';
import { manager } from 'src/server/manager';
import { Logger } from 'src/utils/logger';
import { Queue } from 'src/utils/queue';
import { sleep } from 'src/utils/sleep';

import {
  FileMessageFromBuffer,
  FileMessageFromPath,
  FileMessageFromStream,
  GeneralFileMessage,
} from './types';

const isBig = (fileSize: bigInt.BigInteger): boolean => {
  return fileSize.greaterOrEquals(10 * 1024 * 1024);
};

export abstract class FileUploader<T extends GeneralFileMessage> {
  private fileName: string;
  private fileId: bigInt.BigInteger;

  private isBig: boolean;
  private partCnt: number = 0;
  private readSize: bigInt.BigInteger = bigInt.zero;
  private uploadedSize: bigInt.BigInteger = bigInt.zero;

  private _errors: { [key: number]: Error } = {};

  private _uploadingChunks: Array<{ chunk: Buffer; filePart: number }>;

  constructor(
    protected readonly client: ITDLibClient,
    protected readonly fileSize: bigInt.BigInteger,
    private readonly onComplete: () => Promise<void>,
    private readonly workers: {
      small?: number;
      big?: number;
    } = {
      small: 3,
      big: 15,
    },
  ) {
    this.fileId = generateFileId();
    this.isBig = isBig(fileSize);
    this._uploadingChunks = new Array(
      this.isBig ? this.workers.big : this.workers.small,
    );
  }

  protected abstract get defaultFileName(): string;
  protected abstract prepare(file: T): void;
  protected close(): void {}
  protected abstract read(length: number): Promise<Buffer>;

  private get chunkSize(): bigInt.BigInteger {
    return bigInt(getAppropriatedPartSize(this.fileSize) * 1024);
  }

  private get parts(): number {
    const { quotient, remainder } = this.fileSize.divmod(this.chunkSize);
    return remainder.equals(0)
      ? quotient.toJSNumber()
      : quotient.toJSNumber() + 1;
  }

  private async uploadChunk(
    workerId: number,
    chunk: Buffer,
    filePart: number,
  ): Promise<void> {
    this._uploadingChunks[workerId] = { chunk, filePart };

    while (true) {
      try {
        const rsp = this.isBig
          ? await this.client.saveBigFilePart({
              fileId: this.fileId,
              filePart,
              fileTotalParts: this.parts,
              bytes: chunk,
            })
          : await this.client.saveFilePart({
              fileId: this.fileId,
              filePart,
              bytes: chunk,
            });
        if (rsp.success) {
          this._uploadingChunks[workerId] = null;
          this.uploadedSize = this.uploadedSize.add(chunk.length);
          return;
        }
      } catch (err) {
        if (err instanceof RPCError) {
          if (err.errorMessage === 'FILE_PARTS_INVALID') {
            throw new FileTooBig(this.fileSize);
          }
        }
        Logger.error(`${this.fileName} ${err}`);
      }
    }
  }

  private async saveUncompletedChunks() {
    while (true) {
      const unCompletedChunks = this._uploadingChunks.filter((x) => x !== null);
      if (unCompletedChunks.length === 0) {
        break;
      }

      for (const { chunk, filePart } of unCompletedChunks) {
        if (chunk) {
          await this.uploadChunk(0, chunk, filePart);
        }
      }
    }
  }

  private async uploadNextPart(workerId: number): Promise<bigInt.BigInteger> {
    if (this.done()) {
      return bigInt.zero;
    }

    const chunkLength =
      this.readSize.add(this.chunkSize) > this.fileSize
        ? this.fileSize.minus(this.readSize)
        : this.chunkSize;
    this.readSize = this.readSize.add(chunkLength);
    const filePart = this.partCnt++; // 0-indexed

    if (chunkLength.eq(0)) {
      return bigInt.zero;
    }

    const chunk = await this.read(chunkLength.toJSNumber());

    await this.uploadChunk(workerId, chunk, filePart);

    return chunkLength;
  }

  public async upload(
    file: T,
    callback?: (
      uploaded: bigInt.BigInteger,
      totalSize: bigInt.BigInteger,
    ) => void,
    fileName?: string,
  ): Promise<bigInt.BigInteger> {
    const task = manager.createUploadTask(this.fileName, this.fileSize);
    this.prepare(file);
    try {
      this.fileName = fileName ?? this.defaultFileName;

      const createWorker = async (workerId: number): Promise<boolean> => {
        try {
          while (!this.done()) {
            const partSize = await this.uploadNextPart(workerId);
            Logger.info(
              `[worker ${workerId}] ${this.uploadedSize
                .multiply(100)
                .divide(this.fileSize)
                .toJSNumber()}% uploaded ${this.fileId}(${this.fileName})`,
            );

            if (partSize && callback) {
              callback(this.readSize, this.fileSize);
            }
          }

          return true;
        } catch (err) {
          this._errors[workerId] = err;
          return false;
        }
      };

      while (this.uploadedSize < this.fileSize) {
        const promises: Array<Promise<boolean>> = [];

        const numWorkers = this.isBig ? this.workers.big : this.workers.small;
        for (let i = 0; i < numWorkers; i++) {
          promises.push(createWorker(i));
        }

        await Promise.all(promises);
        await this.saveUncompletedChunks();
      }

      await sleep(500); // sleep 500ms before sending the file message, otherwise Telegram reports FILE_PART_0_MISSING error.
      await this.onComplete();
    } finally {
      this.close();

      task.errors = this.errors;
      task.complete();

      return this.fileSize;
    }
  }

  private done(): boolean {
    return this.readSize >= this.fileSize;
  }

  public get errors(): Array<Error> {
    return Object.values(this._errors);
  }

  public async send(
    chatId: number,
    caption?: string,
  ): Promise<SendMessageResp> {
    Logger.info(`sending file ${this.fileName}`);

    if (Object.keys(this._errors).length > 0) {
      throw new AggregatedError(this.errors);
    }

    const req = {
      chatId,
      file: this.getUploadedFile(),
      name: this.fileName,
      caption,
    };
    if (this.isBig) {
      return await this.client.sendBigFile(req);
    } else {
      return await this.client.sendSmallFile(req);
    }
  }

  public getUploadedFile(): UploadedFile {
    return {
      id: this.fileId,
      parts: this.parts,
      name: this.fileName,
    };
  }
}

export class UploaderFromPath extends FileUploader<FileMessageFromPath> {
  private _filePath: string;
  private _file: number;
  private _read: number = 0;

  protected prepare(fileMsg: FileMessageFromPath) {
    const { path } = fileMsg;
    this._filePath = path;
    this._file = fs.openSync(path, 'r');
  }

  protected close() {
    fs.closeSync(this._file);
  }

  protected get defaultFileName(): string {
    return path.basename(this._filePath);
  }

  protected async read(length: number): Promise<Buffer> {
    const buffer = Buffer.alloc(length);
    fs.readSync(this._file, buffer, 0, length, this._read);
    this._read += length;
    return buffer;
  }
}

export class UploaderFromBuffer extends FileUploader<FileMessageFromBuffer> {
  private buffer: Buffer;
  private _read: number = 0;

  protected get defaultFileName(): string {
    return 'unnamed';
  }

  protected prepare(fileMsg: FileMessageFromBuffer) {
    this.buffer = fileMsg.buffer;
  }

  protected async read(length: number): Promise<Buffer> {
    const res = this.buffer.subarray(this._read, this._read + length);
    this._read += length;
    return res;
  }
}

export class UploaderFromStream extends FileUploader<FileMessageFromStream> {
  private stream: Readable;
  private chunks: Queue<Buffer> = new Queue();
  private readyLength = 0;

  private requests: Queue<{
    resolve: (buffer: Buffer) => void;
    length: number;
  }> = new Queue();

  protected get defaultFileName(): string {
    return 'unnamed';
  }

  private readFromChunks(length: number): Buffer {
    let prepared = 0;
    const preparedChunks = [];
    while (prepared < length) {
      const chunk = this.chunks.dequeue();
      if (chunk.length + prepared > length) {
        const sliced = chunk.subarray(0, length - prepared);
        preparedChunks.push(sliced);
        this.chunks.enqueueFront(chunk.subarray(length - prepared));
        prepared += sliced.length;
      } else {
        prepared += chunk.length;
        preparedChunks.push(chunk);
      }
    }
    return Buffer.concat(preparedChunks);
  }

  protected prepare(fileMsg: FileMessageFromStream): void {
    this.stream = fileMsg.stream;
    this.stream.on('data', (chunk) => {
      if (chunk) {
        this.chunks.enqueue(chunk);
        this.readyLength += chunk.length;
      }
      while (true) {
        const req = this.requests.peek();
        if (!req) {
          this.stream.pause();
          break;
        }
        if (req.length <= this.readyLength) {
          req.resolve(this.readFromChunks(req.length));
          this.readyLength -= req.length;
          this.requests.dequeue();
        } else {
          break;
        }
      }
    });
  }

  protected async read(length: number): Promise<Buffer> {
    if (this.stream.readableEnded) {
      return null;
    }
    if (this.stream.isPaused()) {
      this.stream.resume();
    }
    return new Promise((resolve) => {
      this.requests.enqueue({ resolve, length });
    });
  }
}

export function getUploader(
  tdlib: TDLibApi,
  fileMsg: GeneralFileMessage,
  onComplete: () => Promise<void> = async () => {},
): FileUploader<GeneralFileMessage> {
  const selectApi = (fileSize: bigInt.BigInteger) => {
    // bot cannot upload files larger than 50MB
    return fileSize.greater(50 * 1024 * 1024) ? tdlib.account : tdlib.bot;
  };

  if ('path' in fileMsg) {
    const fileSize = bigInt(fs.statSync(fileMsg.path).size);
    return new UploaderFromPath(selectApi(fileSize), fileSize, onComplete);
  } else if ('buffer' in fileMsg) {
    const fileSize = bigInt(fileMsg.buffer.length);
    return new UploaderFromBuffer(selectApi(fileSize), fileSize, onComplete);
  } else if ('stream' in fileMsg) {
    const fileSize = bigInt(fileMsg.size);
    return new UploaderFromStream(selectApi(fileSize), fileSize, onComplete);
  }
}
