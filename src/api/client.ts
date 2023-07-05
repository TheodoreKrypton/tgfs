import { Api, TelegramClient } from 'telegram';
import { CustomFile } from 'telegram/client/uploads';
import { FileLike } from 'telegram/define';

import { DirectoryAlreadyExistsError } from '../errors/directory';
import { FileIsEmptyError } from '../errors/file';
import { TGFSDirectory } from '../model/directory';
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
}
