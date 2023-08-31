import { Readable, Writable } from 'stream';

import {
  CreateInfo,
  CreationDateInfo,
  DeleteInfo,
  Errors,
  FileSystem,
  FileSystemSerializer,
  ILockManager,
  IPropertyManager,
  LastModifiedDateInfo,
  LocalLockManager,
  LocalPropertyManager,
  LockManagerInfo,
  OpenReadStreamInfo,
  OpenWriteStreamInfo,
  Path,
  PropertyManagerInfo,
  ReadDirInfo,
  ResourceType,
  ReturnCallback,
  SimpleCallback,
  SizeInfo,
  TypeInfo,
} from 'webdav-server/lib/index.v2';

import { Client } from 'src/api';
import {
  createDir,
  list,
  removeDir,
  removeFile,
  uploadFromBytes,
} from 'src/api/ops';
import { createEmptyFile } from 'src/api/ops/create-empty-file';
import { loginAsBot } from 'src/auth';
import {
  FileOrDirectoryAlreadyExistsError,
  FileOrDirectoryDoesNotExistError,
  InvalidNameError,
} from 'src/errors';
import { TGFSDirectory, TGFSFileRef } from 'src/model/directory';
import { Logger } from 'src/utils/logger';

const lockManager = new LocalLockManager();

export class TGFSSerializer implements FileSystemSerializer {
  uid(): string {
    return 'TGFSSerializer-1.0.0';
  }

  serialize(fileSystem: TGFSFileSystem, callback: ReturnCallback<any>): void {
    callback(null, {});
  }

  unserialize(serializedData: any, callback: ReturnCallback<FileSystem>): void {
    (async () => {
      const client = await loginAsBot();
      await client.init();
      const fileSystem = new TGFSFileSystem(serializedData.rootPath);
      callback(null, fileSystem);
    })();
  }
}

const handleError = (callback: (e) => any) => (err) => {
  if (err instanceof FileOrDirectoryAlreadyExistsError) {
    callback(Errors.ResourceAlreadyExists);
  } else if (err instanceof FileOrDirectoryDoesNotExistError) {
    callback(Errors.ResourceNotFound);
  } else if (err instanceof InvalidNameError) {
    callback(Errors.IllegalArguments);
  } else {
    callback(Errors.InvalidOperation);
  }
};

const call =
  (callback: SimpleCallback) =>
  (
    promise: Promise<any>,
    then: (...args: any) => any = () => callback(null),
  ) => {
    promise.then(then).catch((e) => {
      handleError(callback)(e);
      Logger.error(e);
    });
  };

export class TGFSFileSystem extends FileSystem {
  constructor(public readonly tgClient: Client) {
    super(new TGFSSerializer());
  }

  protected _create(
    path: Path,
    ctx: CreateInfo,
    callback: SimpleCallback,
  ): void {
    if (ctx.type.isDirectory) {
      call(callback)(createDir(this.tgClient)(path.toString(), false));
    } else {
      call(callback)(createEmptyFile(this.tgClient)(path.toString()));
    }
  }

  protected _delete(
    path: Path,
    ctx: DeleteInfo,
    callback: SimpleCallback,
  ): void {
    this.type(ctx.context, path, (e, type) => {
      if (e) return callback(Errors.ResourceNotFound);
      if (type.isDirectory) {
        call(callback)(removeDir(this.tgClient)(path.toString(), true));
      } else {
        call(callback)(removeFile(this.tgClient)(path.toString()));
      }
    });
  }

  protected _size(
    path: Path,
    ctx: SizeInfo,
    callback: ReturnCallback<number>,
  ): void {
    (async () => {
      try {
        const res = await list(this.tgClient)(path.toString());
        if (!Array.isArray(res)) {
          const fileDesc = await this.tgClient.getFileDesc(res);
          if (fileDesc.isEmptyFile()) {
            callback(null, 0);
          } else {
            callback(null, fileDesc.getLatest().size);
          }
        } else {
          callback(null, 0);
        }
      } catch (err) {
        handleError(callback)(err);
        Logger.error(err);
      }
    })();
  }

  protected _readDir(
    path: Path,
    ctx: ReadDirInfo,
    callback: ReturnCallback<string[] | Path[]>,
  ): void {
    (async () => {
      try {
        const res = await list(this.tgClient)(path.toString());
        callback(
          null,
          (res as Array<TGFSFileRef | TGFSDirectory>).map((item) => item.name),
        );
      } catch (err) {
        handleError(callback)(err);
        Logger.error(err);
      }
    })();
  }

  protected getStatDateProperty(
    path: Path,
    ctx: any,
    propertyName: string,
    callback: ReturnCallback<number>,
  ): void {
    (async () => {
      try {
        const res = await list(this.tgClient)(path.toString());
        if (!Array.isArray(res)) {
          const fileDesc = await this.tgClient.getFileDesc(res);
          if (propertyName === 'mtime') {
            if (fileDesc.isEmptyFile()) {
              callback(null, Date.now());
            } else {
              callback(null, fileDesc.getLatest().updatedAt.getTime());
            }
          } else {
            callback(null, fileDesc.createdAt.getTime());
          }
        } else {
          callback(null, 0);
        }
      } catch (err) {
        handleError(callback)(err);
        Logger.error(err);
      }
    })();
  }

  protected _creationDate(
    path: Path,
    ctx: CreationDateInfo,
    callback: ReturnCallback<number>,
  ): void {
    this.getStatDateProperty(path, ctx, 'birthtime', callback);
  }

  protected _lastModifiedDate(
    path: Path,
    ctx: LastModifiedDateInfo,
    callback: ReturnCallback<number>,
  ): void {
    this.getStatDateProperty(path, ctx, 'mtime', callback);
  }

  protected _lockManager(
    path: Path,
    ctx: LockManagerInfo,
    callback: ReturnCallback<ILockManager>,
  ): void {
    callback(null, lockManager);
  }

  protected _propertyManager(
    path: Path,
    ctx: PropertyManagerInfo,
    callback: ReturnCallback<IPropertyManager>,
  ): void {
    callback(null, new LocalPropertyManager());
  }

  protected _type(
    path: Path,
    ctx: TypeInfo,
    callback: ReturnCallback<ResourceType>,
  ): void {
    (async () => {
      try {
        const res = await list(this.tgClient)(path.toString());
        if (Array.isArray(res)) {
          callback(null, ResourceType.Directory);
        } else {
          callback(null, ResourceType.File);
        }
      } catch (err) {
        handleError(callback)(err);
        Logger.error(err);
      }
    })();
  }

  protected _openWriteStream(
    path: Path,
    ctx: OpenWriteStreamInfo,
    callback: ReturnCallback<Writable>,
  ): void {
    const chunks = [];
    const tgClient = this.tgClient;
    const writable = new Writable({
      write(chunk, encoding, next) {
        chunks.push(chunk);
        next();
      },
      final(cb) {
        const buffer = Buffer.concat(chunks);
        if (buffer.length > 0) {
          call(cb)(
            uploadFromBytes(tgClient)(Buffer.concat(chunks), path.toString()),
          );
        } else {
          call(cb)(createEmptyFile(tgClient)(path.toString()));
        }
      },
    });
    callback(null, writable);
  }

  protected _openReadStream(
    path: Path,
    ctx: OpenReadStreamInfo,
    callback: ReturnCallback<Readable>,
  ): void {
    (async () => {
      try {
        const fileRef = await list(this.tgClient)(path.toString());
        if (fileRef instanceof TGFSFileRef) {
          const fileDesc = await this.tgClient.getFileDesc(fileRef);
          const fileVersion = fileDesc.getLatest();
          const buffer = await this.tgClient.downloadFileVersion(
            fileVersion,
            fileDesc.name,
          );
          callback(null, Readable.from(buffer));
        } else {
          callback(Errors.InvalidOperation);
        }
      } catch (err) {
        handleError(callback)(err);
        Logger.error(err);
      }
    })();
  }
}
