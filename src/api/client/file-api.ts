import { TGFSDirectory, TGFSFileRef } from 'src/model/directory';
import { TGFSFileVersion } from 'src/model/file';
import { validateName } from 'src/utils/validate-name';

import { DirectoryApi } from './directory-api';
import { GeneralFileMessage, isFileMessageEmpty } from './message-api/types';

export class FileApi extends DirectoryApi {
  private async createFile(where: TGFSDirectory, fileMsg: GeneralFileMessage) {
    validateName(fileMsg.name);

    const id = await this.createFileDesc(fileMsg);
    const fr = where.createFileRef(fileMsg.name, id);

    await this.syncMetadata();

    return fr;
  }

  private async updateFile(
    fr: TGFSFileRef,
    fileMsg: GeneralFileMessage,
    versionId?: string,
  ) {
    const fd = await this.getFileDesc(fr, false);

    if (!isFileMessageEmpty(fileMsg)) {
      let id: number = null;
      id = await this.sendFile(fileMsg);

      if (!versionId) {
        fd.addVersionFromFileMessageId(id);
      } else {
        const fv = fd.getVersion(versionId);
        fv.messageId = id;

        fd.updateVersion(fv);
      }
    } else {
      if (!versionId) {
        fd.addEmptyVersion();
      } else {
        const fv = fd.getVersion(versionId);
        fv.setInvalid();
        fd.updateVersion(fv);
      }
    }

    await this.updateFileDesc(fr, fd);

    return fr;
  }

  public async deleteFile(fr: TGFSFileRef, version?: string) {
    if (!version) {
      fr.delete();
      await this.syncMetadata();
    } else {
      const fd = await this.getFileDesc(fr, false);
      fd.deleteVersion(version);
      await this.updateFileDesc(fr, fd);
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
