import { TelegramClient } from 'telegram';

import { Telegram } from 'telegraf';

import { FileApi } from './file-api';

export class Client extends FileApi {
  constructor(
    protected readonly account: TelegramClient,
    protected readonly bot: Telegram,
  ) {
    super(account, bot);
  }

  public async init() {
    await this.initMetadata();
    if (!this.getRootDirectory()) {
      await this.createRootDirectory();
    }
  }
}
