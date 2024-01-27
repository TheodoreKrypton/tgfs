import fs from 'fs';

import { TelegramClient } from 'telegram';

import { Telegram } from 'telegraf';

import { TGFSDirectory, TGFSFileRef } from 'src/model/directory';
import { TGFSFileVersion } from 'src/model/file';
import { validateName } from 'src/utils/validate-name';

import { DirectoryApi } from './directory-api';

export class FileApi extends DirectoryApi {
  constructor(
    protected readonly account: TelegramClient,
    protected readonly bot: Telegram,
  ) {
    super(account, bot);
  }

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

  private writeContent(content: Buffer, outputFile?: string | fs.WriteStream) {
    if (!outputFile) {
      return;
    }
    if (outputFile instanceof fs.WriteStream) {
      outputFile.write(content);
      outputFile.end();
    } else {
      fs.writeFileSync(outputFile, content);
    }
  }

  public async downloadLatestVersion(
    fr: TGFSFileRef,
    asName: string,
    outputFile?: string | fs.WriteStream,
  ): Promise<Buffer> {
    const fd = await this.getFileDesc(fr);
    let res = Buffer.from('');
    if (fd.isEmptyFile()) {
      this.writeContent(res, outputFile);
    } else {
      const version = fd.getLatest();
      return await this.downloadFileVersion(version, asName, outputFile);
    }
    return res;
  }

  public async downloadFileVersion(
    fv: TGFSFileVersion,
    asName: string,
    outputFile?: string | fs.WriteStream,
  ): Promise<Buffer> {
    const res = await this.downloadFile({
      messageId: fv.messageId,
      name: asName,
    });
    if (outputFile) {
      this.writeContent(res, outputFile);
    }
    return res;
  }
}
