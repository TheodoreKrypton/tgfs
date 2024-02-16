import { BigInteger } from 'big-integer';

type InputMessage = { file?: BigInteger; message?: string };
type Message = {
  id: number;
  text?: string;
  document?: { id: BigInteger };
};

export class MockMessages {
  messages: {
    [key: number]: Message;
  } = {};
  messageId: number = 1;
  pinnedMessageId: number;
  fileParts: { [fileId: string]: { [part: number]: Buffer } } = {};

  saveFilePart(fileId: BigInteger, part: number, data: Buffer) {
    if (!this.fileParts[String(fileId)]) {
      this.fileParts[String(fileId)] = {};
    }
    this.fileParts[String(fileId)][part] = data;
    return { success: true };
  }

  sendMessage(msg: InputMessage) {
    const { file, message } = msg;

    const messageId = ++this.messageId;

    this.messages[messageId] = {
      id: messageId,
      text: message,
      document: {
        id: file,
      },
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

  getFile(fileId: BigInteger) {
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
      this.messages[messageId].document = { id: file };
    }
  }

  search(kw: string) {
    return Object.values(this.messages).filter(
      (msg: any) => msg.text?.includes(kw),
    );
  }
}
