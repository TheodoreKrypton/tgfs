import { TelegramClient } from 'telegram';

import { config } from 'src/config';

export class MessageApi {
  protected readonly privateChannelId = config.telegram.private_file_channel;

  constructor(protected readonly client: TelegramClient) {}

  protected async send(message: string) {
    return await this.client.sendMessage(this.privateChannelId, {
      message,
    });
  }

  protected async getMessagesByIds(messageIds: number[]) {
    return await this.client.getMessages(this.privateChannelId, {
      ids: messageIds,
    });
  }
}
