import { Api } from 'telegram';
import { CustomFile } from 'telegram/client/uploads';

import { TGFSDirectory } from '../../model/directory';
import { TGFSMetadata } from '../../model/metadata';
import { FileApi } from './file-api';

export class MetaDataApi extends FileApi {
  protected metadata: TGFSMetadata;

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
      await this.client.getMessages(this.privateChannelId, {
        filter: new Api.InputMessagesFilterPinned(),
      })
    )[0];

    if (!pinnedMessage) {
      return null;
    }
    const metadata = TGFSMetadata.fromObject(
      JSON.parse(
        String(
          await this.downloadMediaByMessageId(
            { messageId: pinnedMessage.id, name: 'metadata.json' },
            false,
          ),
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

  protected async updateMetadata() {
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

  public getRootDirectory() {
    return this.metadata.dir;
  }
}
