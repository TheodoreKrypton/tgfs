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

  protected async updateMetadata() {
    const buffer = Buffer.from(JSON.stringify(this.metadata.toObject()));
    const file = new CustomFile('metadata.json', buffer.length, '', buffer);
    if (this.metadata.msgId) {
      return await this.editMessage(this.metadata.msgId, { file });
    } else {
      const message = await this.sendMessage({
        file,
      });
      this.metadata.msgId = message.id;
      await this.pinMessage(message.id);
      return message;
    }
  }

  public getRootDirectory() {
    return this.metadata.dir;
  }
}
