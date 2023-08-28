import { TelegramClient } from 'telegram';

import { FileApi } from './file-api';

export class Client extends FileApi {
  constructor(protected readonly client: TelegramClient) {
    super(client);
  }

  public async init() {
    await this.initMetadata();
    if (!this.getRootDirectory()) {
      await this.createRootDirectory();
    }
  }
}
