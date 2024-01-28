type InputMessage = { file?: any; message?: string };
type Message = { id: number; text?: string; document?: any };

export class MockMessages {
  messages: {
    [key: number]: Message;
  } = {};
  messageId: number = 1;
  pinnedMessageId: number;

  files: any = {};
  fileId: number = 1;

  createFile(file: any) {
    const fileId = ++this.fileId;
    if (file instanceof Buffer) {
      this.files[fileId] = {
        id: fileId,
        size: file.length,
        buffer: file,
      };
    } else {
      this.files[fileId] = {
        id: fileId,
        ...file,
      };
    }
    return {
      id: fileId,
      size: this.files[fileId].size,
    };
  }

  sendMessage(msg: InputMessage) {
    const { file, message } = msg;

    const messageId = ++this.messageId;

    this.messages[messageId] = {
      id: messageId,
      text: message,
    };
    if (file) {
      this.messages[messageId].document = this.createFile(file);
    }
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

  getFile(fileId: number) {
    return this.files[fileId];
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
      this.messages[messageId].document = this.createFile(file);
    }
  }

  search(kw: string) {
    return Object.values(this.messages).filter(
      (msg: any) => msg.text?.includes(kw),
    );
  }
}
