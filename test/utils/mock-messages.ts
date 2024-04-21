import bigInt from 'big-integer';

import * as types from 'src/api/types';

type InputMessage = { file?: bigInt.BigInteger; message?: string };
type Message = {
  id: number;
  text?: string;
  document?: types.Document;
};

export class MockMessages {
  constructor(
    public readonly messages: { [key: number]: Message } = {},
    public messageId: number = 1,
    public pinnedMessageId?: number,
    public fileParts: { [fileId: string]: { [part: number]: Buffer } } = {},
  ) {}

  saveFilePart(fileId: bigInt.BigInteger, part: number, data: Buffer) {
    if (!this.fileParts[String(fileId)]) {
      this.fileParts[String(fileId)] = {};
    }
    this.fileParts[String(fileId)][part] = data;
    return { success: true };
  }

  private fileIdToDocument(fileId: bigInt.BigInteger): types.Document {
    const fileParts = this.fileParts[String(fileId)];
    const size = fileParts
      ? Object.values(fileParts).reduce((acc, part) => acc + part.length, 0)
      : 0;
    return {
      id: fileId,
      size: bigInt(size),
      accessHash: bigInt(0),
      fileReference: Buffer.from(''),
    };
  }

  sendMessage(msg: InputMessage) {
    const { file, message } = msg;

    const messageId = ++this.messageId;

    this.messages[messageId] = {
      id: messageId,
      text: message,
      document: file ? this.fileIdToDocument(file) : undefined,
    };
    return messageId;
  }

  getMessage(messageId: number) {
    const message = this.messages[messageId];
    return {
      id: message.id,
      text: message.text,
      document: message.document,
    };
  }

  getFile(fileId: bigInt.BigInteger) {
    return this.fileParts[String(fileId)];
  }

  editMessage(messageId: number, msg: InputMessage) {
    const { file, message } = msg;
    if (message) {
      this.messages[messageId] = {
        ...this.messages[messageId],
        text: message,
      };
    }
    if (file) {
      this.messages[messageId].document = this.fileIdToDocument(file);
    }
  }

  search(kw: string) {
    return Object.values(this.messages).filter((msg: any) =>
      msg.text?.includes(kw),
    );
  }
}
