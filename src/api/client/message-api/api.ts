import { RPCError } from 'telegram/errors';



import { IBot, TDLibApi } from 'src/api/interface';
import { DownloadFileResp, MessageResp } from 'src/api/types';
import { config } from 'src/config';
import { MessageNotFound } from 'src/errors/telegram';
import { flowControl } from 'src/utils/flow-control';

import { MessageBroker } from './message-broker';

export class MessageApi extends MessageBroker {
  constructor(
    public readonly tdlib: TDLibApi,
    public readonly bot: IBot,
  ) {
    super(tdlib);
  }

  @flowControl()
  public async sendText(message: string): Promise<number> {
    return (
      await this.tdlib.bot.sendText({
        chatId: this.privateChannelId,
        text: message,
      })
    ).messageId;
  }

  @flowControl()
  public async editMessageText(
    messageId: number,
    message: string,
  ): Promise<number> {
    try {
      return (
        await this.tdlib.bot.editMessageText({
          chatId: this.privateChannelId,
          messageId,
          text: message,
        })
      ).messageId;
    } catch (err) {
      if (err instanceof RPCError) {
        if (err.message === 'message to edit not found') {
          throw new MessageNotFound(messageId);
        }
        if (err.errorMessage === 'MESSAGE_NOT_MODIFIED') {
          return messageId;
        }
      }
      throw err;
    }
  }

  public async getPinnedMessage(): Promise<MessageResp> {
    return (
      await this.tdlib.account.getPinnedMessages({
        chatId: this.privateChannelId,
      })
    )[0];
  }

  public async pinMessage(messageId: number) {
    return await this.tdlib.bot.pinMessage({
      chatId: this.privateChannelId,
      messageId,
    });
  }

  public async searchMessages(search: string): Promise<MessageResp[]> {
    return await this.tdlib.account.searchMessages({
      chatId: this.privateChannelId,
      search,
    });
  }

  public downloadFile(messageId: number): Promise<DownloadFileResp> {
    return this.tdlib.account.downloadFile({
      chatId: this.privateChannelId,
      messageId: messageId,
      chunkSize: config.tgfs.download.chunk_size_kb,
    });
  }
}