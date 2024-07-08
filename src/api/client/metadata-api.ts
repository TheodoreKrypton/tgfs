import { TGFSDirectory } from 'src/model/directory';
import { TGFSMetadata } from 'src/model/metadata';

import { IMetaDataRepository } from './repository/interface';

export class MetaDataApi {
  private metadata: TGFSMetadata;

  constructor(private metadataRepo: IMetaDataRepository) {}

  public async init() {
    this.metadata = await this.metadataRepo.get();
    if (!this.metadata) {
      this.metadata = new TGFSMetadata();
    }
    if (!this.getRootDirectory()) {
      await this.resetMetadata();
      await this.syncMetadata();
    }
  }

  public async resetMetadata() {
    this.metadata.dir = new TGFSDirectory('root', null);
  }

  public async syncMetadata() {
    this.metadata.syncWith(await this.metadataRepo.get());
    await this.updateMetadata();
  }

  private async updateMetadata(): Promise<undefined> {
    this.metadata.msgId = await this.metadataRepo.save(this.metadata);
  }

  public getRootDirectory() {
    return this.metadata.dir;
  }
}
