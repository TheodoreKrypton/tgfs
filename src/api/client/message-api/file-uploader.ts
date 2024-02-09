import fs from 'fs';

import bigInt from 'big-integer';
import path from 'path';

import { ITDLibApi } from 'src/api/interface';
import { SendMessageResp, UploadedFile } from 'src/api/types';
import { generateFileId, getAppropriatedPartSize } from 'src/api/utils';
import { TechnicalError } from 'src/errors/base';
import { Logger } from 'src/utils/logger';

const isBig = (fileSize: number): boolean => {
  return fileSize >= 50 * 1024 * 1024;
};

abstract class FileUploader {
  private fileName: string;
  private fileId: bigInt.BigInteger;

  private partCnt: number = 0;
  private uploaded: number = 0;

  constructor(protected readonly tdlib: ITDLibApi) {
    this.fileId = generateFileId();
  }

  protected abstract defaultFileName(): string;
  protected abstract fileSize(): number;
  protected abstract open(file: string | Buffer): void;
  protected close(): void {}
  protected abstract read(length: number): Promise<Buffer>;

  private chunkSize(): number {
    return getAppropriatedPartSize(bigInt(this.fileSize())) * 1024;
  }

  private parts(): number {
    return Math.ceil(this.fileSize() / this.chunkSize());
  }

  private async uploadNextPart(workerId: number): Promise<number> {
    if (this.done()) {
      return 0;
    }

    const chunkLength =
      this.uploaded + this.chunkSize() > this.fileSize()
        ? this.fileSize() - this.uploaded
        : this.chunkSize();

    const chunk = await this.read(chunkLength);

    this.uploaded += chunkLength;
    this.partCnt += 1;

    let retry = 3;
    while (retry) {
      try {
        const rsp = await this.tdlib.saveBigFilePart({
          fileId: this.fileId,
          filePart: this.partCnt - 1, // 0-indexed
          fileTotalParts: this.parts(),
          bytes: chunk,
        });
        if (!rsp.success) {
          throw new TechnicalError(
            `File chunk ${this.partCnt} of ${this.fileName} failed to upload`,
          );
        }
        return chunkLength;
      } catch (err) {
        Logger.error(`error encountered ${workerId} ${err} ${retry}`);

        retry -= 1;
        if (retry === 0) {
          throw err;
        }
      }
    }
  }

  public async upload(
    file: string | Buffer,
    callback?: (uploaded: number, totalSize: number) => void,
    fileName?: string,
    workers: number = 15,
  ): Promise<void> {
    this.open(file);
    try {
      this.fileName = fileName ?? this.defaultFileName();

      if (isBig(this.fileSize())) {
        const createWorker = async (workerId: number): Promise<void> => {
          while (!this.done()) {
            await this.uploadNextPart(workerId);
            if (callback) {
              callback(this.uploaded, this.fileSize());
            }
          }
        };

        const promises: Array<Promise<void>> = [];
        for (let i = 0; i < workers; i++) {
          promises.push(createWorker(i));
        }

        await Promise.all(promises);
      } else {
        await this.tdlib.saveFilePart({
          fileId: this.fileId,
          bytes: await this.read(this.fileSize()),
        });
      }
    } finally {
      this.close();
    }
  }

  private done(): boolean {
    return this.uploaded >= this.fileSize();
  }

  public async send(
    chatId: number,
    caption?: string,
  ): Promise<SendMessageResp> {
    const req = {
      chatId,
      file: this.getUploadedFile(),
      name: this.fileName,
      caption,
    };
    if (isBig(this.fileSize())) {
      return await this.tdlib.sendBigFile(req);
    } else {
      return await this.tdlib.sendSmallFile(req);
    }
  }

  public getUploadedFile(): UploadedFile {
    return {
      id: this.fileId,
      parts: this.parts(),
      name: this.fileName,
    };
  }
}

export class UploaderFromPath extends FileUploader {
  private _filePath: string;
  private _fileSize: number;
  private _file: number;
  private _read: number = 0;

  constructor(protected readonly tdlib: ITDLibApi) {
    super(tdlib);
  }

  protected open(filePath: string) {
    this._filePath = filePath;
    this._fileSize = fs.statSync(filePath).size;
    this._file = fs.openSync(filePath, 'r');
  }

  protected close() {
    fs.closeSync(this._file);
  }

  protected defaultFileName(): string {
    return path.basename(this._filePath);
  }

  protected fileSize(): number {
    return this._fileSize;
  }

  protected async read(length: number): Promise<Buffer> {
    const buffer = Buffer.alloc(length);
    fs.readSync(this._file, buffer, 0, length, this._read);
    this._read += length;
    return buffer;
  }
}

export class UploaderFromBuffer extends FileUploader {
  private buffer: Buffer;
  private _read: number = 0;

  constructor(protected readonly tdlib: ITDLibApi) {
    super(tdlib);
  }

  protected defaultFileName(): string {
    return 'unnamed';
  }

  protected open(buffer: Buffer) {
    this.buffer = buffer;
  }

  protected fileSize(): number {
    return this.buffer.length;
  }

  protected read(length: number): Promise<Buffer>;

  protected async read(length: number): Promise<Buffer> {
    const res = this.buffer.subarray(this._read, this._read + length);
    this._read += length;
    return res;
  }
}
