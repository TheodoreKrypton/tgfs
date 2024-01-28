import { Telegram } from 'telegraf';

import { IBotApi } from 'src/api/interface';
import * as types from 'src/api/types';
import { Config } from 'src/config';

export const createBot = (config: Config): Telegram => {
  return new Telegram(config.telegram.bot.token);
};

export class TelegrafApi implements IBotApi {
  constructor(protected readonly bot: Telegram) {}

  public async sendText(
    req: types.SendTextReq,
  ): Promise<types.SendMessageResp> {
    const rsp = await this.bot.sendMessage(req.chatId, req.text);
    return {
      messageId: rsp.message_id,
    };
  }

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

  public async editMessageMedia(
    req: types.EditMessageMediaReq,
  ): Promise<types.SendMessageResp> {
    await this.bot.editMessageMedia(req.chatId, req.messageId, undefined, {
      type: 'document',
      media: {
        source: req.buffer,
      },
    });
    return {
      messageId: req.messageId,
    };
  }

  public async pinMessage(req: types.PinMessageReq): Promise<void> {
    await this.bot.pinChatMessage(req.chatId, req.messageId);
  }

  public async sendFileFromBuffer(
    req: types.SendFileFromBufferReq,
  ): Promise<types.SendMessageResp> {
    const rsp = await this.bot.sendDocument(req.chatId, {
      source: req.buffer,
      filename: req.name,
    });
    return {
      messageId: rsp.message_id,
    };
  }

  public async sendFileFromPath(
    req: types.SendFileFromPathReq,
  ): Promise<types.SendMessageResp> {
    const rsp = await this.bot.sendDocument(req.chatId, {
      source: req.filePath,
    });
    return {
      messageId: rsp.message_id,
    };
  }
}
