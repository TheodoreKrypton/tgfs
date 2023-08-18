import { TelegramClient } from 'telegram';
import { FileLike } from 'telegram/define';

import { TGFSDirectory, TGFSFileRef } from '../../model/directory';
import { TGFSFile } from '../../model/file';
import { validateName } from '../../utils/validate-name';
import { DirectoryApi } from './directory-api';

export class Client extends DirectoryApi {
  constructor(protected readonly client: TelegramClient) {
    super(client);
  }

  public async init() {
    await this.initMetadata();
    if (!this.getRootDirectory()) {
      await this.createRootDirectory();
    }
  }

  public async newFileUnder(
    name: string,
    where: TGFSDirectory,
    file: FileLike,
  ) {
    validateName(name);

    const uploadFileMsg = await this.sendFile(file);

    const tgfsFile = new TGFSFile(name);
    tgfsFile.addVersionFromFileMessage(uploadFileMsg);

    const tgfsFileMsg = await this.send(JSON.stringify(tgfsFile.toObject()));

    const tgfsFileRef = where.createFileRef(name, tgfsFileMsg);

    await this.syncMetadata();

    return tgfsFileRef;
  }

  public async updateFile(
    tgfsFileRef: TGFSFileRef,
    file: FileLike,
    versionId?: string,
  ) {
    const tgfsFile = await this.getFileFromFileRef(tgfsFileRef);

    const uploadFileMsg = await this.sendFile(file);

    if (!versionId) {
      tgfsFile.addVersionFromFileMessage(uploadFileMsg);
    } else {
      const tgfsFileVersion = tgfsFile.getVersion(versionId);
      tgfsFileVersion.messageId = uploadFileMsg.id;
      tgfsFile.updateVersion(tgfsFileVersion);
    }

    this.client.editMessage(this.privateChannelId, {
      message: tgfsFileRef.getMessageId(),
      text: JSON.stringify(tgfsFile.toObject()),
    });

    await this.syncMetadata();

    return tgfsFileRef;
  }

  public async putFileUnder(
    name: string,
    where: TGFSDirectory,
    file: FileLike,
  ) {
    const tgfsFileRef = where.findFiles([name])[0];
    if (tgfsFileRef) {
      return await this.updateFile(tgfsFileRef, file);
    } else {
      return await this.newFileUnder(name, where, file);
    }
  }

  public async deleteFileAtVersion(tgfsFileRef: TGFSFileRef, version?: string) {
    if (!version) {
      tgfsFileRef.delete();
    } else {
      const tgfsFile = await this.getFileFromFileRef(tgfsFileRef);
      tgfsFile.deleteVersion(version);
      await this.client.editMessage(this.privateChannelId, {
        message: tgfsFileRef.getMessageId(),
        text: JSON.stringify(tgfsFile.toObject()),
      });
    }
    await this.syncMetadata();
  }
}
