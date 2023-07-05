import { Api, TelegramClient } from 'telegram';
import { CustomFile } from 'telegram/client/uploads';
import { FileLike } from 'telegram/define';

import { DirectoryAlreadyExistsError } from '../errors/directory';
import { FileAlreadyExistsError } from '../errors/file';
import { FileIsEmptyError } from '../errors/file';
import { TGFSDirectory, TGFSFileRef } from '../model/directory';
import { TGFSFile, TGFSFileVersion } from '../model/file';
import { TGFSMetadata } from '../model/metadata';

export class Client {
  metadata: TGFSMetadata;

  constructor(
    public readonly client: TelegramClient,
    private readonly privateChannelId: string,
    private readonly publicChannelId?: string,
  ) {}

  public async init() {
    this.metadata = await this.getMetadata();
  }

  public async send(message: string) {
    return await this.client.sendMessage(this.privateChannelId, {
      message,
    });
  }

  public async getMessagesByIds(messageIds: number[]) {
    return await this.client.getMessages(this.privateChannelId, {
      ids: messageIds,
    });
  }

  public async getObjectsByMessageIds(messageIds: number[]) {
    return (await this.getMessagesByIds(messageIds)).map((message) =>
      JSON.parse(message.text),
    );
  }

  public async getFileAtVersion(
    fileRef: TGFSFileRef,
    versionId?: string,
  ): Promise<Api.Document> {
    const tgfsFile = TGFSFile.fromObject(
      (await this.getObjectsByMessageIds([fileRef.messageId]))[0],
    );
    if (versionId) {
      return tgfsFile.getVersion(versionId);
    } else {
      return tgfsFile.getLatest();
    }
  }

  public async downloadFile(document: Api.Document, outputFile?: string) {
    const options = {};
    if (outputFile) {
      options['outputFile'] = outputFile;
    }
    return await this.client.downloadFile(
      new Api.InputDocumentFileLocation({
        id: document.id,
        accessHash: document.accessHash,
        fileReference: document.fileReference,
        thumbSize: '',
      }),
      options,
    );
  }

  private async downloadMetadata() {
    const pinnedMessage = (
      await this.client.getMessages(this.privateChannelId, {
        filter: new Api.InputMessagesFilterPinned(),
      })
    )[0];
    const document = (pinnedMessage.media as Api.MessageMediaDocument).document;
    if (!(document instanceof Api.DocumentEmpty)) {
      return {
        metadataString: String(await this.downloadFile(document)),
        msgId: pinnedMessage.id,
      };
    } else {
      throw new FileIsEmptyError('metadata.json');
    }
  }

  public async getMetadata() {
    const { metadataString, msgId } = await this.downloadMetadata();
    const metadata = TGFSMetadata.fromMetadataString(metadataString);
    metadata.msgId = msgId;
    return metadata;
  }

  public async sendFile(file: FileLike) {
    return await this.client.sendFile(this.privateChannelId, {
      file,
      workers: 16,
    });
  }

  public async updateMetadata() {
    const buffer = Buffer.from(this.metadata.toMetadataString());
    return await this.client.editMessage(this.privateChannelId, {
      message: this.metadata.msgId,
      file: new CustomFile('metadata.json', buffer.length, '', buffer),
    });
  }

  public async createDirectoryUnder(name: string, where: TGFSDirectory) {
    if (where.children.find((child) => child.name === name)) {
      throw new DirectoryAlreadyExistsError(name);
    }

    const newDirectory = new TGFSDirectory(name, where, []);
    where.children.push(newDirectory);
    return newDirectory;
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
    const media = uploadFileMsg.media as Api.MessageMediaDocument;

    if (media.document instanceof Api.DocumentEmpty) {
      throw new FileIsEmptyError(name);
    }

    const tgfsFile = new TGFSFile(name);
    const tgfsFileVersion = await TGFSFileVersion.fromDocument(media.document);
    tgfsFile.addVersion(tgfsFileVersion);

    const tgfsFileMsg = await this.send(JSON.stringify(tgfsFile.toObject()));

    const tgfsFileRef = new TGFSFileRef(tgfsFileMsg.id, tgfsFile.name, where);
    where.files.push(tgfsFileRef);

    await this.updateMetadata();

    return tgfsFileRef;
  }
}
