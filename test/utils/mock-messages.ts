export class MockMessages {
  messages: any = {};
  messageId: number = 1;
  pinnedMessageId: number;

  sendMessage(msg: any) {
    const { file, message } = msg;

    const messageId = ++this.messageId;
    this.messages[messageId] = {
      id: messageId,
      text: message,
      document:
        file instanceof Buffer
          ? { id: messageId, buffer: file, size: file.length }
          : { id: messageId, ...file },
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

  editMessage(messageId: number, msg: any) {
    const { file, text } = msg;
    this.messages[messageId] = {
      ...this.messages[messageId],
      text,
      document:
        file instanceof Buffer
          ? { id: messageId, buffer: file, size: file.length }
          : { id: messageId, ...file },
    };
  }
}
