import { Api } from 'telegram';

import { TDLibApi } from 'src/api/interface';
import { config } from 'src/config';

export class MessageBroker {
  public readonly privateChannelId = Number(
    config.telegram.private_file_channel,
  );

  constructor(
    protected readonly tdlib: TDLibApi,
    protected requests: Array<{
      ids: number[];
      resolve: (result: unknown) => void;
      reject: (error: unknown) => void;
    }> = [],
    protected timeout: NodeJS.Timeout = null,
  ) {}

  async getMessages(ids: number[]): Promise<Api.Message[]> {
    return new Promise((resolve, reject) => {
      this.requests.push({ ids, resolve, reject });
      if (this.timeout) {
        clearTimeout(this.timeout);
      }
      this.timeout = setTimeout(async () => {
        let requests = [];
        [requests, this.requests] = [[...this.requests], []];
        const ids = [...new Set(requests.map((item) => item.ids).flat())];

        try {
          const messages = await this.tdlib.account.getMessages({
            chatId: this.privateChannelId,
            messageIds: ids,
          });
          const messageMap = new Map();
          messages.forEach((message) => {
            if (message) {
              messageMap.set(message.messageId, message);
            }
          });
          requests.forEach((request) => {
            const result = request.ids.map((id: number) => messageMap.get(id));
            request.resolve(result);
          });
        } catch (err) {
          requests.forEach((request) => {
            request.reject(err);
          });
        }
      }, 100);
    });
  }
}
