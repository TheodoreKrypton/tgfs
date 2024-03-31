import { TGFSDirectory, TGFSFileRef } from 'src/model/directory';
import { TGFSFileVersion } from 'src/model/file';
import { validateName } from 'src/utils/validate-name';

import { DirectoryApi } from './directory-api';
import { GeneralFileMessage } from './message-api/types';

export class FileApi extends DirectoryApi {
  private async createFile(where: TGFSDirectory, fileMsg: GeneralFileMessage) {
    validateName(fileMsg.name);

    const id = await this.createFileDesc(fileMsg);
    const fr = where.createFileRef(fileMsg.name, id);

    await this.syncMetadata();

    return fr;
  }

  private async updateFileRefMessageIdIfNecessary(
    fr: TGFSFileRef,
    messageId: number,
  ) {
    if (fr.getMessageId() !== messageId) {
      // original file description message is gone
      fr.setMessageId(messageId);
      await this.syncMetadata();
    }
  }

  private async updateFile(
    fr: TGFSFileRef,
    fileMsg: GeneralFileMessage,
    versionId?: string,
  ) {
    const messageId = versionId
      ? await this.updateFileVersion(fr, fileMsg, versionId)
      : await this.addFileVersion(fr, fileMsg);
    await this.updateFileRefMessageIdIfNecessary(fr, messageId);
    return fr;
  }

  public async deleteFile(fr: TGFSFileRef, version?: string) {
    if (!version) {
      fr.delete();
      await this.syncMetadata();
    } else {
      const messageId = await this.deleteFileVersion(fr, version);
      await this.updateFileRefMessageIdIfNecessary(fr, messageId);
    }
  }

  public async uploadFile(
    where: {
      under: TGFSDirectory;
      versionId?: string;
    },
    file?: GeneralFileMessage,
  ) {
    const fr = where.under.findFiles([file.name])[0];
    if (fr) {
      return await this.updateFile(fr, file, where.versionId);
    } else {
      return await this.createFile(where.under, file);
    }
  }

  public async *downloadLatestVersion(
    fr: TGFSFileRef,
    asName: string,
  ): AsyncGenerator<Buffer> {
    const fd = await this.getFileDesc(fr);

    if (fd.isEmptyFile()) {
      yield Buffer.from('');
    } else {
      const version = fd.getLatest();
      yield* this.downloadFileVersion(version, asName);
    }
  }

  public downloadFileVersion(
    fv: TGFSFileVersion,
    asName: string,
  ): AsyncGenerator<Buffer> {
    return this.downloadFile(asName, fv.messageId);
  }
}
