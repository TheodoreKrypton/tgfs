import { ITDLibClient } from 'src/api/interface';
import * as types from 'src/api/types';

import { Messages } from './messages';

export class FakeGramJSApi implements ITDLibClient {
  constructor(private messages: Messages) {}

  public async getMessages(
    req: types.GetMessagesReq,
  ): Promise<types.GetMessagesResp> {
    return req.messageIds.map((messageId) => {
      const message = this.messages.getMessage(messageId);

      return {
        messageId,
        text: message.text,
        document: message.document,
      };
    });
  }

  public async sendText(
    req: types.SendTextReq,
  ): Promise<types.SendMessageResp> {
    const messageId = this.messages.sendMessage({ message: req.text });
    return { messageId };
  }

  public async editMessageText(
    req: types.EditMessageTextReq,
  ): Promise<types.SendMessageResp> {
    const message = this.messages.getMessage(req.messageId);
    this.messages.editMessage(req.messageId, {
      message: req.text,
      file: message.document?.id,
    });
    return { messageId: req.messageId };
  }

  public async searchMessages(
    req: types.SearchMessagesReq,
  ): Promise<types.GetMessagesResp> {
    const messages = this.messages.search(req.search);
    return messages.map((message) => {
      return {
        messageId: message.id,
        text: message.text,
      };
    });
  }

  public async getPinnedMessages(
    req: types.GetPinnedMessagesReq,
  ): Promise<types.GetMessagesResp> {
    if (!this.messages.pinnedMessageId) {
      return [];
    }
    const message = this.messages.getMessage(this.messages.pinnedMessageId);
    return [
      {
        messageId: message.id,
        text: message.text,
      },
    ];
  }

  public async pinMessage(req: types.PinMessageReq): Promise<void> {
    this.messages.pinnedMessageId = req.messageId;
  }

  public async saveBigFilePart(
    req: types.SaveBigFilePartReq,
  ): Promise<types.SaveFilePartResp> {
    return this.messages.saveFilePart(req.fileId, req.filePart, req.bytes);
  }

  public async saveFilePart(
    req: types.SaveFilePartReq,
  ): Promise<types.SaveFilePartResp> {
    return this.messages.saveFilePart(req.fileId, req.filePart, req.bytes);
  }

  public async sendBigFile(
    req: types.SendFileReq,
  ): Promise<types.SendMessageResp> {
    const messageId = this.messages.sendMessage({ file: req.file.id });
    return { messageId };
  }

  public async sendSmallFile(
    req: types.SendFileReq,
  ): Promise<types.SendMessageResp> {
    const messageId = this.messages.sendMessage({ file: req.file.id });
    return { messageId };
  }

  public async editMessageMedia(
    req: types.EditMessageMediaReq,
  ): Promise<types.Message> {
    const message = this.messages.getMessage(req.messageId);
    this.messages.editMessage(req.messageId, {
      message: req.caption ?? message.text,
      file: req.file.id,
    });
    return { messageId: req.messageId };
  }

  public async downloadFile(
    req: types.DownloadFileReq,
  ): Promise<types.DownloadFileResp> {
    const message = this.messages.getMessage(req.messageId);
    const fileId = message.document.id;
    const parts = this.messages.getFile(fileId);
    const chunks = (async function* () {
      const len = Object.keys(parts).length;
      for (let i = 0; i < len; i++) {
        yield parts[i];
      }
    })();
    return {
      chunks,
      size: message.document.size,
    };
  }
}
