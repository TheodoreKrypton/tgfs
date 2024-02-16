import { Telegram } from 'telegraf';

import { IBot } from 'src/api/interface';
import * as types from 'src/api/types';
import { Config } from 'src/config';
import { Logger } from 'src/utils/logger';

export const createBot = (config: Config): Telegram => {
  return new Telegram(config.telegram.bot.token);
};

function retry(retries: number = 10) {
  return function (
    target: any,
    propertyKey: string,
    descriptor: PropertyDescriptor,
  ) {
    const original = descriptor.value;
    descriptor.value = async function (...args: any[]) {
      while (retries > 0) {
        try {
          return await original.apply(this, args);
        } catch (err) {
          retries--;
          Logger.error(`${propertyKey} failed: ${err.message}, retrying...`);
          if (retries === 0) {
            throw err;
          }
        }
      }
    };
  };
}

export class TelegrafApi implements IBot {
  constructor(protected readonly bot: Telegram) {}

  @retry()
  public async sendText(
    req: types.SendTextReq,
  ): Promise<types.SendMessageResp> {
    const rsp = await this.bot.sendMessage(req.chatId, req.text);
    return {
      messageId: rsp.message_id,
    };
  }

  @retry()
  public async editMessageText(
    req: types.EditMessageTextReq,
  ): Promise<types.SendMessageResp> {
    await this.bot.editMessageText(
      req.chatId,
      req.messageId,
      undefined,
      req.text,
    );
    return {
      messageId: req.messageId,
    };
  }

  @retry()
  public async editMessageMedia(
    req: types.EditMessageMediaReq,
  ): Promise<types.SendMessageResp> {
    await this.bot.editMessageMedia(req.chatId, req.messageId, undefined, {
      type: 'document',
      media: {
        filename: req.name,
        source: req.buffer,
      },
      caption: req.caption,
    });
    return {
      messageId: req.messageId,
    };
  }

  @retry()
  public async pinMessage(req: types.PinMessageReq): Promise<void> {
    await this.bot.pinChatMessage(req.chatId, req.messageId);
  }
}
