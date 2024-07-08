import { MessageApi } from 'src/api/client/message-api';
import { IMetaDataRepository } from 'src/api/client/repository/interface';
import { saveToBuffer } from 'src/api/utils';
import { TGFSMetadata } from 'src/model/metadata';

import { FileRepository } from '../file';

export class MetadataRepository implements IMetaDataRepository {
  constructor(
    private readonly msgApi: MessageApi,
    private readonly fileRepo: FileRepository,
  ) {}

  async save(metadata: TGFSMetadata): Promise<number> {
    const buffer = Buffer.from(JSON.stringify(metadata.toObject()));
    if (metadata.msgId) {
      // update current metadata
      return await this.fileRepo.update(
        metadata.msgId,
        buffer,
        'metadata.json',
        '',
      );
    } else {
      // doesn't exist, create new metadata and pin
      const { messageId } = await this.fileRepo.save({
        buffer,
        name: 'metadata.json',
      });
      await this.msgApi.pinMessage(messageId);
      return messageId;
    }
  }

  async get(): Promise<TGFSMetadata | null> {
    const pinnedMessage = await this.msgApi.getPinnedMessage();
    if (!pinnedMessage) {
      return null;
    }
    const metadata = TGFSMetadata.fromObject(
      JSON.parse(
        String(
          await saveToBuffer(
            this.fileRepo.downloadFile(
              'metadata.json',
              pinnedMessage.messageId,
            ),
          ),
        ),
      ),
    );
    metadata.msgId = pinnedMessage.messageId;
    return metadata;
  }
}
