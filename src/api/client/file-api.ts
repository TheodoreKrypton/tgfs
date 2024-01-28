import { TGFSDirectory, TGFSFileRef } from 'src/model/directory';
import { TGFSFileVersion } from 'src/model/file';
import { validateName } from 'src/utils/validate-name';

import { DirectoryApi } from './directory-api';

export class FileApi extends DirectoryApi {
  private async createFile(
    name: string,
    where: TGFSDirectory,
    fileContent?: string | Buffer,
  ) {
    validateName(name);

    const id = await this.createFileDesc(name, fileContent);
    const fr = where.createFileRef(name, id);

    await this.syncMetadata();

    return fr;
  }

  private async updateFile(
    fr: TGFSFileRef,
    file?: string | Buffer,
    versionId?: string,
  ) {
    const fd = await this.getFileDesc(fr, false);

    if (file) {
      const id = await this.sendFile(file);

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
      name: string;
      under: TGFSDirectory;
      versionId?: string;
    },
    file?: string | Buffer,
  ) {
    const fr = where.under.findFiles([where.name])[0];
    if (fr) {
      return await this.updateFile(fr, file, where.versionId);
    } else {
      return await this.createFile(where.name, where.under, file);
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
