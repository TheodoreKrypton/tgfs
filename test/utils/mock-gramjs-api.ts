import { ITDLibClient } from 'src/api/interface';
import * as types from 'src/api/types';

import { MockMessages } from './mock-messages';

export class MockGramJSApi implements ITDLibClient {
  constructor(private messages: MockMessages) {}

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
