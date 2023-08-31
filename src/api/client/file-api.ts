import { TelegramClient } from 'telegram';
import { FileLike } from 'telegram/define';

import fs from 'fs';

import { TGFSDirectory, TGFSFileRef } from 'src/model/directory';
import { TGFSFileVersion } from 'src/model/file';
import { validateName } from 'src/utils/validate-name';

import { DirectoryApi } from './directory-api';

export class FileApi extends DirectoryApi {
  constructor(protected readonly client: TelegramClient) {
    super(client);
  }

  private async createFile(
    name: string,
    where: TGFSDirectory,
    fileContent?: FileLike,
  ) {
    validateName(name);

    const fdMsg = await this.createFileDesc(name, fileContent);
    const tgfsFileRef = where.createFileRef(name, fdMsg);

    await this.syncMetadata();

    return tgfsFileRef;
  }

  private async updateFile(
    tgfsFileRef: TGFSFileRef,
    file?: FileLike,
    versionId?: string,
  ) {
    const fd = await this.getFileDesc(tgfsFileRef, false);

    if (file) {
      const uploadFileMsg = await this.sendFile(file);

      if (!versionId) {
        fd.addVersionFromFileMessage(uploadFileMsg);
      } else {
        const tgfsFileVersion = fd.getVersion(versionId);
        tgfsFileVersion.messageId = uploadFileMsg.id;
        fd.updateVersion(tgfsFileVersion);
      }
    } else {
      if (!versionId) {
        fd.addEmptyVersion();
      } else {
        const tgfsFileVersion = fd.getVersion(versionId);
        tgfsFileVersion.messageId = TGFSFileVersion.EMPTY_FILE;
        fd.updateVersion(tgfsFileVersion);
      }
    }

    await this.updateFileDesc(tgfsFileRef, fd);

    return tgfsFileRef;
  }

  public async deleteFile(tgfsFileRef: TGFSFileRef, version?: string) {
    if (!version) {
      tgfsFileRef.delete();
      await this.syncMetadata();
    } else {
      const fd = await this.getFileDesc(tgfsFileRef, false);
      fd.deleteVersion(version);
      await this.updateFileDesc(tgfsFileRef, fd);
    }
  }

  public async uploadFile(
    where: {
      name: string;
      under: TGFSDirectory;
      versionId?: string;
    },
    file?: FileLike,
  ) {
    const fr = where.under.findFiles([where.name])[0];
    if (fr) {
      return await this.updateFile(fr, file, where.versionId);
    } else {
      return await this.createFile(where.name, where.under, file);
    }
  }

  private writeContent(content: Buffer, outputFile?: string | fs.WriteStream) {
    if (outputFile instanceof fs.WriteStream) {
      outputFile.write(content);
      outputFile.end();
    } else {
      fs.writeFileSync(outputFile, content);
    }
  }

  public async downloadLatestVersion(
    fileRef: TGFSFileRef,
    asName: string,
    outputFile?: string | fs.WriteStream,
  ): Promise<Buffer> {
    const fileDesc = await this.getFileDesc(fileRef);
    let res = Buffer.from('');
    if (fileDesc.isEmptyFile()) {
      this.writeContent(res, outputFile);
    } else {
      const version = fileDesc.getLatest();
      return await this.downloadFileVersion(version, asName, outputFile);
    }
    return res;
  }

  public async downloadFileVersion(
    fileVersion: TGFSFileVersion,
    asName: string,
    outputFile?: string | fs.WriteStream,
  ): Promise<Buffer> {
    const res = await this.downloadFile(
      { messageId: fileVersion.messageId, name: asName },
      true,
    );
    if (outputFile) {
      this.writeContent(res, outputFile);
    }
    return res;
  }
}
