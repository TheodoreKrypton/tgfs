import { EditMessageParams, SendMessageParams } from 'telegram/client/messages';

export class MockMessages {
  messages: any = {};
  messageId: number = 1;
  pinnedMessageId: number;

  sendMessage(msg: SendMessageParams) {
    const { file, message } = msg;
    let f: any = file;

    if (file instanceof Buffer) {
      // file can be CustomFile or a plain buffer
      f = {
        buffer: file,
      };
    }

    const messageId = ++this.messageId;
    this.messages[messageId] = {
      id: messageId,
      text: message,
      file: f,
    };
    return messageId;
  }

  getMessage(messageId: number) {
    const message = this.messages[messageId];
    return {
      id: message.id,
      text: message.text,
      file: message.file?.buffer ?? message.file,
    };
  }

  editMessage(messageId: number, msg: EditMessageParams) {
    const { file, text } = msg;
    this.messages[messageId] = {
      ...this.messages[messageId],
      text,
      file,
    };
  }
}
