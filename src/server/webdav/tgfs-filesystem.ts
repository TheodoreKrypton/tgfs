import { PassThrough, Readable, Writable } from 'stream';

import {
  CreateInfo,
  DeleteInfo,
  Errors,
  FileSystem,
  FileSystemSerializer,
  LocalLockManager,
  LocalPropertyManager,
  MoveInfo,
  OpenReadStreamInfo,
  OpenWriteStreamInfo,
  Path,
  ReadDirInfo,
  RequestContext,
  ResourceType,
  ReturnCallback,
  SimpleCallback,
  VirtualFileSystem,
  VirtualFileSystemResource,
} from 'webdav-server/lib/index.v2';

import { Client } from 'src/api';
import { createDir, list, moveFile, removeDir, removeFile } from 'src/api/ops';
import { createEmptyFile } from 'src/api/ops/create-empty-file';
import { uploadFromStream } from 'src/api/ops/upload';
import { BusinessError } from 'src/errors/base';
import { TGFSDirectory, TGFSFileRef } from 'src/model/directory';
import { TGFSFile } from 'src/model/file';
import { Logger } from 'src/utils/logger';

export class TGFSSerializer implements FileSystemSerializer {
  constructor(private readonly client: Client) {}

  uid(): string {
    return 'TGFSSerializer-1.0.0';
  }

  serialize(fileSystem: TGFSFileSystem, callback: ReturnCallback<any>): void {
    callback(null, {});
  }

  unserialize(serializedData: any, callback: ReturnCallback<FileSystem>): void {
    const fileSystem = new TGFSFileSystem(this.client);
    callback(null, fileSystem);
  }
}

class TGFSFileResource extends VirtualFileSystemResource {
  constructor({
    size = 0,
    lastModifiedDate = 0,
    creationDate = 0,
  }: Partial<VirtualFileSystemResource>) {
    const props = new LocalPropertyManager();

    super({
      props,
      locks: new LocalLockManager(),
      content: [],
      size,
      lastModifiedDate,
      creationDate,
      type: ResourceType.File,
    });
  }

  static fromFileDesc(fd: TGFSFile) {
    const latestVersion = fd.getLatest();

    return new TGFSFileResource({
      size: latestVersion.size,
      lastModifiedDate: latestVersion.updatedAt.getTime(),
      creationDate: fd.createdAt.getTime(),
    });
  }
}

class TGFSDirResource extends VirtualFileSystemResource {
  constructor() {
    const props = new LocalPropertyManager();

    super({
      props,
      locks: new LocalLockManager(),
      content: [],
      size: 0,
      lastModifiedDate: 0,
      creationDate: 0,
      type: ResourceType.Directory,
    });
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

export class TGFSFileSystem extends VirtualFileSystem {
  resources: { [path: string]: VirtualFileSystemResource } = {};

  constructor(public readonly tgClient: Client) {
    super(new TGFSSerializer(tgClient));

    this.resources['/'] = new TGFSDirResource();
  }

  protected _fastExistCheck(
    ctx: RequestContext,
    path: Path,
    callback: (exists: boolean) => void,
  ): void {
    if (this.resources[path.toString()]) {
      callback(true);
    } else {
      this.list(path.toString())
        .then(() => {
          callback(true);
        })
        .catch(() => {
          callback(false);
        });
    }
  }

  private async list(
    path: string,
  ): Promise<TGFSFileRef | (TGFSFileRef | TGFSDirectory)[]> {
    const res = await list(this.tgClient)(path.toString());
    if (res instanceof TGFSFileRef) {
      const fd = await this.tgClient.getFileDesc(res);
      this.resources[path.toString()] = TGFSFileResource.fromFileDesc(fd);
    } else {
      this.resources[path.toString()] = new TGFSDirResource();

      const basePath = path.toString() === '/' ? '/' : `${path.toString()}/`;

      res
        .filter((res) => res instanceof TGFSDirectory)
        .forEach((dir) => {
          this.resources[`${basePath}${dir.name}`] = new TGFSDirResource();
        });

      const promises = res
        .filter((res) => res instanceof TGFSFileRef)
        .map((fr) => {
          return (async () => {
            const fd = await this.tgClient.getFileDesc(fr as TGFSFileRef);
            if (path.toString() === '/') {
              this.resources[`/${fr.name}`] = TGFSFileResource.fromFileDesc(fd);
            } else {
              this.resources[`${basePath}${fr.name}`] =
                TGFSFileResource.fromFileDesc(fd);
            }
          })();
        });

      await Promise.all(promises);
    }
    return res;
  }

  protected _create(
    path: Path,
    ctx: CreateInfo,
    callback: SimpleCallback,
  ): void {
    if (ctx.type.isDirectory) {
      this.resources[path.toString()] = new TGFSDirResource();
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
    const sPath = path.toString(true);
    for (const path in this.resources) {
      if (path.startsWith(sPath)) {
        this.resources[path] = undefined;
      }
    }

    const resource = this.resources[path.toString()];
    this.resources[path.toString()] = undefined;

    if (!resource) {
      return callback(Errors.ResourceNotFound);
    } else if (resource instanceof TGFSDirResource) {
      call(callback)(removeDir(this.tgClient)(path.toString(), true));
    } else {
      call(callback)(removeFile(this.tgClient)(path.toString()));
    }
  }

  protected _readDir(
    path: Path,
    ctx: ReadDirInfo,
    callback: ReturnCallback<string[] | Path[]>,
  ): void {
    (async () => {
      try {
        const res = (await this.list(path.toString())) as (
          | TGFSFileRef
          | TGFSDirectory
        )[];

        callback(
          null,
          res.map((item) => item.name),
        );
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

        if ( estimatedSize <= 0 ) {
          Logger.info('skip upload because file is 0 bytes');
          return;
        }

        try {
          // this.resources[path.toString()] = new TGFSFileResource({
          //   size: estimatedSize,
          // });

          const fd = await uploadFromStream(tgClient)(
            stream,
            estimatedSize,
            path.toString(),
          );

          this.resources[path.toString()] = TGFSFileResource.fromFileDesc(fd);
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
