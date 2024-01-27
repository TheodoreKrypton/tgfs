import { Api } from 'telegram';
import { CustomFile } from 'telegram/client/uploads';

import { TGFSDirectory } from 'src/model/directory';
import { TGFSMetadata } from 'src/model/metadata';

import { FileDescApi } from './file-desc-api';

export class MetaDataApi extends FileDescApi {
  private metadata: TGFSMetadata;

  protected async initMetadata() {
    this.metadata = await this.getMetadata();
    if (!this.metadata) {
      this.metadata = new TGFSMetadata();
    }
  }

  protected async resetMetadata() {
    this.metadata.dir = new TGFSDirectory('root', null);
  }

  protected async getMetadata() {
    const pinnedMessage = (
      await this.getMessages({
        filter: new Api.InputMessagesFilterPinned(),
      })
    )[0];

    if (!pinnedMessage) {
      return null;
    }
    const metadata = TGFSMetadata.fromObject(
      JSON.parse(
        String(
          await this.downloadFile({
            messageId: pinnedMessage.id,
            name: 'metadata.json',
          }),
        ),
      ),
    );
    metadata.msgId = pinnedMessage.id;
    return metadata;
  }

  protected async syncMetadata() {
    this.metadata.syncWith(await this.getMetadata());

    await this.updateMetadata();
  }

  protected async updateMetadata(): Promise<undefined> {
    const buffer = Buffer.from(JSON.stringify(this.metadata.toObject()));
    if (this.metadata.msgId) {
      await this.editMessageMedia(this.metadata.msgId, buffer);
    } else {
      const messageId = await this.sendFile(buffer);
      this.metadata.msgId = messageId;
      await this.pinMessage(messageId);
    }
  }

  public getRootDirectory() {
    return this.metadata.dir;
  }
}
