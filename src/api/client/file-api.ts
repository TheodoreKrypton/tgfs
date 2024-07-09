import { TGFSDirectory, TGFSFileRef } from 'src/model/directory';
import { TGFSFile, TGFSFileVersion } from 'src/model/file';
import { validateName } from 'src/utils/validate-name';

import { FileDescApi } from './file-desc-api';
import { MetaDataApi } from './metadata-api';
import { GeneralFileMessage } from './model';

export class FileApi {
  constructor(
    private readonly metadataApi: MetaDataApi,
    private readonly fileDescApi: FileDescApi,
  ) {}

  public async copy(
    where: TGFSDirectory,
    fr: TGFSFileRef,
    name?: string,
  ): Promise<TGFSFileRef> {
    const copiedFR = where.createFileRef(name ?? fr.name, fr.getMessageId());
    await this.metadataApi.syncMetadata();
    return copiedFR;
  }

  private async create(
    where: TGFSDirectory,
    fileMsg: GeneralFileMessage,
  ): Promise<TGFSFile> {
    validateName(fileMsg.name);

    const { messageId, fd } = await this.fileDescApi.createFileDesc(fileMsg);
    where.createFileRef(fileMsg.name, messageId);
    await this.metadataApi.syncMetadata();
    return fd;
  }

  private async updateFileRefMessageIdIfNecessary(
    fr: TGFSFileRef,
    messageId: number,
  ): Promise<void> {
    if (fr.getMessageId() !== messageId) {
      // original file description message is gone
      fr.setMessageId(messageId);
      await this.metadataApi.syncMetadata();
    }
  }

  private async update(
    fr: TGFSFileRef,
    fileMsg: GeneralFileMessage,
    versionId?: string,
  ): Promise<TGFSFile> {
    const { messageId, fd } = versionId
      ? await this.fileDescApi.updateFileVersion(fr, fileMsg, versionId)
      : await this.fileDescApi.addFileVersion(fr, fileMsg);
    await this.updateFileRefMessageIdIfNecessary(fr, messageId);
    return fd;
  }

  public async rm(fr: TGFSFileRef, version?: string): Promise<void> {
    if (!version) {
      fr.delete();
      await this.metadataApi.syncMetadata();
    } else {
      const { messageId } = await this.fileDescApi.deleteFileVersion(
        fr,
        version,
      );
      await this.updateFileRefMessageIdIfNecessary(fr, messageId);
    }
  }

  public async upload(
    where: {
      under: TGFSDirectory;
      versionId?: string;
    },
    fileMsg?: GeneralFileMessage,
  ): Promise<TGFSFile> {
    const fr = where.under.findFiles([fileMsg.name])[0];
    if (fr) {
      return await this.update(fr, fileMsg, where.versionId);
    } else {
      return await this.create(where.under, fileMsg);
    }
  }

  public async *retrieve(
    fr: TGFSFileRef,
    asName?: string,
  ): AsyncGenerator<Buffer> {
    const fd = await this.desc(fr);

    if (fd.isEmptyFile()) {
      yield Buffer.from('');
    } else {
      const version = fd.getLatest();
      yield* this.fileDescApi.downloadFileAtVersion(asName ?? fr.name, version);
    }
  }

  public async *retrieveVersion(
    version: TGFSFileVersion,
    asName: string,
  ): AsyncGenerator<Buffer> {
    yield* this.fileDescApi.downloadFileAtVersion(asName, version);
  }

  public async desc(fr: TGFSFileRef): Promise<TGFSFile> {
    return await this.fileDescApi.getFileDesc(fr);
  }
}
