import { TGFSDirectory, TGFSFileRef } from 'src/model/directory';
import { TGFSFile } from 'src/model/file';
import { validateName } from 'src/utils/validate-name';

import { FileDescApi } from './file-desc-api';
import { MetaDataApi } from './metadata-api';
import { GeneralFileMessage } from './model';

export class FileRefApi {
  constructor(
    private readonly metadataApi: MetaDataApi,
    private readonly fileDescApi: FileDescApi,
  ) {}

  public async copyFile(
    where: TGFSDirectory,
    fr: TGFSFileRef,
    name?: string,
  ): Promise<TGFSFileRef> {
    const copiedFR = where.createFileRef(name ?? fr.name, fr.getMessageId());
    await this.metadataApi.syncMetadata();
    return copiedFR;
  }

  private async createFile(
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

  private async updateFile(
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

  public async deleteFile(fr: TGFSFileRef, version?: string): Promise<void> {
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

  public async uploadFile(
    where: {
      under: TGFSDirectory;
      versionId?: string;
    },
    fileMsg?: GeneralFileMessage,
  ): Promise<TGFSFile> {
    const fr = where.under.findFiles([fileMsg.name])[0];
    if (fr) {
      return await this.updateFile(fr, fileMsg, where.versionId);
    } else {
      return await this.createFile(where.under, fileMsg);
    }
  }
}
