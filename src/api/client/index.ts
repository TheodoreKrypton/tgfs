import { gramjs, telegraf } from 'src/api/impl';
import { config } from 'src/config';
import { TGFSDirectory, TGFSFileRef } from 'src/model/directory';
import { TGFSFile } from 'src/model/file';

import { DirectoryApi } from './directory-api';
import { FileDescApi } from './file-desc-api';
import { FileRefApi } from './file-ref-api';
import { MessageApi } from './message-api';
import { MetaDataApi } from './metadata-api';
import { GeneralFileMessage } from './model';
import { TGMsgFDRepository } from './repository/impl/fd/tg-msg';
import { FileRepository } from './repository/impl/file';
import { MetadataRepository } from './repository/impl/metadata/tg-msg';

export const createClient = async () => {
  const api = {
    tdlib: {
      account: new gramjs.GramJSApi(await gramjs.loginAsAccount(config)),
      bot: new gramjs.GramJSApi(await gramjs.loginAsBot(config)),
    },
    bot: new telegraf.TelegrafApi(telegraf.createBot(config)),
  };

  const msgApi = new MessageApi(api.tdlib, api.bot);

  const fileRepo = new FileRepository(msgApi);
  const fdRepo = new TGMsgFDRepository(msgApi);
  const metadataRepo = new MetadataRepository(msgApi, fileRepo);

  const fdApi = new FileDescApi(fdRepo, fileRepo);

  const metadataApi = new MetaDataApi(metadataRepo);
  await metadataApi.init();

  const frApi = new FileRefApi(metadataApi, fdApi);
  const dirApi = new DirectoryApi(metadataApi);

  return new Client(metadataApi, frApi, fdApi, dirApi, fileRepo);
};

export class Client {
  constructor(
    private readonly metadataApi: MetaDataApi,
    private readonly frApi: FileRefApi,
    private readonly fdApi: FileDescApi,
    private readonly dirApi: DirectoryApi,
    private readonly fileRepo: FileRepository,
  ) {}

  public async *downloadLatestVersion(
    fr: TGFSFileRef,
    asName: string,
  ): AsyncGenerator<Buffer> {
    const fd = await this.fdApi.getFileDesc(fr);

    if (fd.isEmptyFile()) {
      yield Buffer.from('');
    } else {
      const version = fd.getLatest();
      yield* this.fileRepo.downloadFile(asName, version.messageId);
    }
  }

  public async getFileDesc(fr: TGFSFileRef) {
    return this.fdApi.getFileDesc(fr);
  }

  public getRootDirectory() {
    return this.metadataApi.getRootDirectory();
  }

  public async createDirectory(
    where: { name: string; under: TGFSDirectory },
    dir?: TGFSDirectory,
  ) {
    return this.dirApi.createDirectory(where, dir);
  }

  public findDirs(dir: TGFSDirectory) {
    return dir.findDirs();
  }

  public async copyFile(
    where: TGFSDirectory,
    fr: TGFSFileRef,
    name?: string,
  ): Promise<TGFSFileRef> {
    return this.frApi.copyFile(where, fr, name);
  }

  public async uploadFile(
    where: {
      under: TGFSDirectory;
      versionId?: string;
    },
    fileMsg?: GeneralFileMessage,
  ): Promise<TGFSFile> {
    return this.frApi.uploadFile(where, fileMsg);
  }

  public async ls(
    dir: TGFSDirectory,
    fileName?: string,
  ): Promise<TGFSFileRef | Array<TGFSDirectory | TGFSFileRef>> {
    return this.dirApi.ls(dir, fileName);
  }

  public async deleteEmptyDirectory(directory: TGFSDirectory) {
    return this.dirApi.deleteEmptyDirectory(directory);
  }

  public async dangerouslyDeleteDirectory(directory: TGFSDirectory) {
    return this.dirApi.dangerouslyDeleteDirectory(directory);
  }

  public async deleteFile(fr: TGFSFileRef, version?: string) {
    return this.frApi.deleteFile(fr, version);
  }
}
