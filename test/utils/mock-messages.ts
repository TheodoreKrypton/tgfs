export class MockMessages {
  messages: any = {};
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

  sendMessage(msg: any) {
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

  editMessage(messageId: number, msg: any) {
    const { file, text } = msg;
    this.messages[messageId] = {
      ...this.messages[messageId],
      text,
    };
    if (file) {
      this.messages[messageId].document = this.createFile(file);
    }
  }
}
