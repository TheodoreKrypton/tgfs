import { IBot } from 'src/api/interface';
import * as types from 'src/api/types';
import { generateFileId } from 'src/api/utils';

import { MockMessages } from './mock-messages';

export class MockTelegrafApi implements IBot {
  constructor(private messages: MockMessages) {}

  public async sendText(req: types.SendTextReq): Promise<types.Message> {
    const messageId = this.messages.sendMessage({ message: req.text });
    return { messageId };
  }

  public async editMessageText(
    req: types.EditMessageTextReq,
  ): Promise<types.SendMessageResp> {
    this.messages.editMessage(req.messageId, { message: req.text });
    return { messageId: req.messageId };
  }

  public async editMessageMedia(
    req: types.EditMessageMediaReq,
  ): Promise<types.SendMessageResp> {
    const fileId = generateFileId();
    this.messages.saveFilePart(fileId, 0, req.buffer);

    this.messages.editMessage(req.messageId, {
      file: fileId,
    });
    return { messageId: req.messageId };
  }

  public async pinMessage(req: types.PinMessageReq): Promise<void> {
    this.messages.pinnedMessageId = req.messageId;
  }
}
