import * as fs from 'fs';
import { Api, TelegramClient } from 'telegram';
import { DownloadMediaInterface } from 'telegram/client/downloads';
import { CustomFile } from 'telegram/client/uploads';
import { FileLike } from 'telegram/define';

import { TechnicalError } from '../errors/base';
import { DirectoryAlreadyExistsError } from '../errors/directory';
import { FileAlreadyExistsError } from '../errors/file';
import { TGFSDirectory, TGFSFileRef } from '../model/directory';
import { TGFSFile } from '../model/file';
import { TGFSMetadata } from '../model/metadata';

export class Client {
  metadata: TGFSMetadata;

  constructor(
    protected readonly client: TelegramClient,
    private readonly privateChannelId: string,
    private readonly publicChannelId?: string,
  ) {}

  public async init() {
    this.metadata = await this.getMetadata();
    if (!this.metadata) {
      this.metadata = new TGFSMetadata();
      await this.createEmptyDirectory();
    }
  }

  private async send(message: string) {
    return await this.client.sendMessage(this.privateChannelId, {
      message,
    });
  }

  private async getMessagesByIds(messageIds: number[]) {
    return await this.client.getMessages(this.privateChannelId, {
      ids: messageIds,
    });
  }

  private async getObjectsByMessageIds(messageIds: number[]) {
    return (await this.getMessagesByIds(messageIds)).map((message) =>
      JSON.parse(message.text),
    );
  }

  public async getFileInfo(fileRef: TGFSFileRef): Promise<TGFSFile> {
    const file = await this.getFileFromFileRef(fileRef);
    return file;
  }

  private async downloadMediaById(
    messageIds: number,
    downloadParams?: DownloadMediaInterface,
  ) {
    return await this.client.downloadMedia(
      (
        await this.getMessagesByIds([messageIds])
      )[0],
      downloadParams,
    );
  }

  public async downloadFileAtVersion(
    fileRef: TGFSFileRef,
    versionId?: string,
    outputFile?: fs.PathLike,
  ): Promise<Buffer | null> {
    const tgfsFile = await this.getFileFromFileRef(fileRef);

    const version = versionId
      ? tgfsFile.getVersion(versionId)
      : tgfsFile.getLatest();

    if (outputFile) {
      const ws = fs.createWriteStream(outputFile);
      await this.downloadMediaById(version.messageId, { outputFile: ws });
    } else {
      const res = await this.downloadMediaById(version.messageId);
      if (res instanceof Buffer) {
        return res;
      } else {
        throw new TechnicalError(
          `Downloaded file is not a buffer. ${this.privateChannelId}/${version.messageId}`,
        );
      }
    }
  }

  private async getMetadata() {
    const pinnedMessage = (
      await this.client.getMessages(this.privateChannelId, {
        filter: new Api.InputMessagesFilterPinned(),
      })
    )[0];

    if (!pinnedMessage) {
      return null;
    }

    const metadata = TGFSMetadata.fromObject(
      JSON.parse(String(await this.downloadMediaById(pinnedMessage.id))),
    );
    metadata.msgId = pinnedMessage.id;
    return metadata;
  }

  private async sendFile(file: FileLike) {
    return await this.client.sendFile(this.privateChannelId, {
      file,
      workers: 16,
    });
  }

  private async syncMetadata() {
    this.metadata.syncWith(await this.getMetadata());

    await this.updateMetadata();
  }

  private async updateMetadata() {
    const buffer = Buffer.from(JSON.stringify(this.metadata.toObject()));
    const file = new CustomFile('metadata.json', buffer.length, '', buffer);
    if (this.metadata.msgId) {
      return await this.client.editMessage(this.privateChannelId, {
        message: this.metadata.msgId,
        file,
      });
    } else {
      const message = await this.client.sendMessage(this.privateChannelId, {
        file,
      });
      this.metadata.msgId = message.id;
      await this.client.pinMessage(this.privateChannelId, message.id);
      return message;
    }
  }

  public async createEmptyDirectory() {
    this.metadata.dir = new TGFSDirectory('root', null, []);
    await this.syncMetadata();

    return this.metadata.dir;
  }

  public async createDirectoryUnder(name: string, where: TGFSDirectory) {
    if (where.children.find((child) => child.name === name)) {
      throw new DirectoryAlreadyExistsError(name);
    }

    const newDirectory = new TGFSDirectory(name, where, []);
    where.children.push(newDirectory);

    await this.syncMetadata();

    return newDirectory;
  }

  private async getFileFromFileRef(fileRef: TGFSFileRef) {
    return TGFSFile.fromObject(
      (await this.getObjectsByMessageIds([fileRef.messageId]))[0],
    );
  }

  public async newFileUnder(
    name: string,
    where: TGFSDirectory,
    file: FileLike,
  ) {
    if (where.files.find((file) => file.name === name)) {
      throw new FileAlreadyExistsError(name);
    }

    const uploadFileMsg = await this.sendFile(file);

    const tgfsFile = new TGFSFile(name);
    tgfsFile.addVersionFromFileMessage(uploadFileMsg);

    const tgfsFileMsg = await this.send(JSON.stringify(tgfsFile.toObject()));

    const tgfsFileRef = new TGFSFileRef(tgfsFileMsg.id, tgfsFile.name, where);
    where.files.push(tgfsFileRef);

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
      message: tgfsFileRef.messageId,
      text: JSON.stringify(tgfsFile.toObject()),
    });

    await this.syncMetadata();

    return tgfsFileRef;
  }
}
