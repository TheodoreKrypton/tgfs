import fs from 'fs';
import { Readable } from 'stream';

import { RPCError } from 'telegram/errors';

import bigInt from 'big-integer';
import path from 'path';

import { ITDLibClient, TDLibApi } from 'src/api/interface';
import { SendMessageResp, UploadedFile } from 'src/api/types';
import { Queue, generateFileId, getAppropriatedPartSize } from 'src/api/utils';
import { AggregatedError, TechnicalError } from 'src/errors/base';
import { FileTooBig } from 'src/errors/telegram';
import { Logger } from 'src/utils/logger';

import {
  FileMessageFromBuffer,
  FileMessageFromPath,
  FileMessageFromStream,
  GeneralFileMessage,
} from './types';

const isBig = (fileSize: number): boolean => {
  return fileSize >= 10 * 1024 * 1024;
};

export abstract class FileUploader<T extends GeneralFileMessage> {
  private fileName: string;
  private fileId: bigInt.BigInteger;

  private partCnt: number = 0;
  private uploaded: number = 0;

  private _errors: { [key: number]: Error } = {};

  constructor(
    protected readonly client: ITDLibClient,
    protected readonly fileSize: number,
  ) {
    this.fileId = generateFileId();
  }

  protected abstract get defaultFileName(): string;
  protected abstract prepare(file: T): void;
  protected close(): void {}
  protected abstract read(length: number): Promise<Buffer>;

  private get chunkSize(): number {
    return getAppropriatedPartSize(bigInt(this.fileSize)) * 1024;
  }

  private get parts(): number {
    return Math.ceil(this.fileSize / this.chunkSize);
  }

  private async uploadNextPart(workerId: number): Promise<number> {
    if (this.done()) {
      return 0;
    }

    const chunkLength =
      this.uploaded + this.chunkSize > this.fileSize
        ? this.fileSize - this.uploaded
        : this.chunkSize;

    const chunk = await this.read(chunkLength);

    if (chunk === null) {
      return 0;
    }

    this.uploaded += chunkLength;
    this.partCnt += 1;

    let retry = 3;
    while (retry) {
      try {
        const rsp = await this.client.saveBigFilePart({
          fileId: this.fileId,
          filePart: this.partCnt - 1, // 0-indexed
          fileTotalParts: this.parts,
          bytes: chunk,
        });
        if (!rsp.success) {
          throw new TechnicalError(
            `File chunk ${this.partCnt} of ${this.fileName} failed to upload`,
          );
        }
        return chunkLength;
      } catch (err) {
        if (err instanceof RPCError) {
          if (err.errorMessage === 'FILE_PARTS_INVALID') {
            throw new FileTooBig(this.fileSize);
          }
        }

        Logger.error(
          `error encountered in uploading worker ${workerId}: ${err} retries left: ${retry}`,
        );

        retry -= 1;
        if (retry === 0) {
          throw err;
        }
      }
    }
  }

  public async upload(
    file: T,
    callback?: (uploaded: number, totalSize: number) => void,
    fileName?: string,
    workers: number = 15,
  ): Promise<void> {
    this.prepare(file);
    try {
      this.fileName = fileName ?? this.defaultFileName;

      if (isBig(this.fileSize)) {
        const createWorker = async (workerId: number): Promise<void> => {
          try {
            while (!this.done()) {
              await this.uploadNextPart(workerId);
              if (callback) {
                callback(this.uploaded, this.fileSize);
              }
            }
          } catch (err) {
            this._errors[workerId] = err;
          }
        };

        const promises: Array<Promise<void>> = [];
        for (let i = 0; i < workers; i++) {
          promises.push(createWorker(i));
        }

        await Promise.all(promises);
      } else {
        const bytes = await this.read(this.fileSize);
        await this.client.saveFilePart({
          fileId: this.fileId,
          bytes,
        });
      }
    } finally {
      this.close();
    }
  }

  private done(): boolean {
    return this.uploaded >= this.fileSize;
  }

  public get errors(): Array<Error> {
    return Object.values(this._errors);
  }

  public async send(
    chatId: number,
    caption?: string,
  ): Promise<SendMessageResp> {
    if (Object.keys(this._errors).length > 0) {
      throw new AggregatedError(this.errors);
    }

    const req = {
      chatId,
      file: this.getUploadedFile(),
      name: this.fileName,
      caption,
    };
    if (isBig(this.fileSize)) {
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
): FileUploader<GeneralFileMessage> {
  const selectApi = (fileSize: number) => {
    return fileSize > 50 * 1024 * 1024 ? tdlib.account : tdlib.bot;
  };

  if ('path' in fileMsg) {
    const fileSize = fs.statSync(fileMsg.path).size;
    return new UploaderFromPath(selectApi(fileSize), fileSize);
  } else if ('buffer' in fileMsg) {
    const fileSize = fileMsg.buffer.length;
    return new UploaderFromBuffer(selectApi(fileSize), fileSize);
  } else if ('stream' in fileMsg) {
    const fileSize = fileMsg.size;
    return new UploaderFromStream(selectApi(fileSize), fileSize);
  }
}
