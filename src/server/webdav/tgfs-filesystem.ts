import { PassThrough, Readable, Writable } from 'stream';

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
  MoveInfo,
  OpenReadStreamInfo,
  OpenWriteStreamInfo,
  Path,
  PropertyAttributes,
  PropertyBag,
  PropertyManagerInfo,
  ReadDirInfo,
  ResourcePropertyValue,
  ResourceType,
  Return2Callback,
  ReturnCallback,
  SimpleCallback,
  SizeInfo,
  TypeInfo,
} from 'webdav-server/lib/index.v2';

import { Client, createClient } from 'src/api';
import { createDir, list, moveFile, removeDir, removeFile } from 'src/api/ops';
import { createEmptyFile } from 'src/api/ops/create-empty-file';
import { uploadFromStream } from 'src/api/ops/upload';
import { BusinessError } from 'src/errors/base';
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
      const client = await createClient();
      const fileSystem = new TGFSFileSystem(client);
      callback(null, fileSystem);
    })();
  }
}

const handleError = (callback: (e: Error) => any) => (err: Error) => {
  const castedError = err as BusinessError;
  if (castedError.code == 'FILE_OR_DIR_ALREADY_EXISTS') {
    callback(Errors.ResourceAlreadyExists);
  } else if (castedError.code == 'FILE_OR_DIR_DOES_NOT_EXIST') {
    callback(Errors.ResourceNotFound);
  } else if (castedError.code == 'INVALID_NAME') {
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

class TGFSPropertyManager extends LocalPropertyManager {}

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

  protected _move(
    pathFrom: Path,
    pathTo: Path,
    ctx: MoveInfo,
    callback: ReturnCallback<boolean>,
  ): void {
    (async () => {
      try {
        await moveFile(this.tgClient)(pathFrom.toString(), pathTo.toString());
        callback(null, true);
      } catch (err) {
        handleError(callback)(err);
        Logger.error(err);
      }
    })();
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
            callback(null, fileDesc.getLatest().updatedAt.getTime());
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
    callback(null, new TGFSPropertyManager());
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
    (async () => {
      try {
        const tgClient = this.tgClient;
        const { estimatedSize } = ctx;

        const stream = new PassThrough();

        callback(null, stream);

        try {
          await uploadFromStream(tgClient)(
            stream,
            estimatedSize,
            path.toString(),
          );
        } catch (err) {
          stream.destroy();
          throw err;
        }
      } catch (err) {
        handleError(callback)(err);
        Logger.error(err);
      }
    })();
  }

  protected _openReadStream(
    path: Path,
    ctx: OpenReadStreamInfo,
    callback: ReturnCallback<Readable>,
  ): void {
    (async () => {
      try {
        const fileRef = (await list(this.tgClient)(
          path.toString(),
        )) as TGFSFileRef;
        const chunks = this.tgClient.downloadLatestVersion(
          fileRef,
          fileRef.name,
        );

        callback(null, Readable.from(chunks));
      } catch (err) {
        handleError(callback)(err);
        Logger.error(err);
      }
    })();
  }
}
