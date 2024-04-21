import bigInt from 'big-integer';

import { MockMessages } from './mock-messages';

describe('test mock messages', () => {
  it('should send and get message', () => {
    const mockMessages = new MockMessages();
    const messageId = mockMessages.sendMessage({ message: 'hello' });
    const message = mockMessages.getMessage(messageId);
    expect(message.text).toEqual('hello');
  });

  it('should increase message id after sending message', () => {
    const mockMessages = new MockMessages();
    const messageId1 = mockMessages.sendMessage({ message: 'hello' });
    const messageId2 = mockMessages.sendMessage({ message: 'world' });
    expect(messageId2).toBeGreaterThan(messageId1);
  });

  it('should send and get message with file', () => {
    const mockMessages = new MockMessages();
    const fileId = bigInt(123);
    const messageId = mockMessages.sendMessage({
      message: 'hello',
      file: fileId,
    });
    const message = mockMessages.getMessage(messageId);
    expect(message.document.id).toEqual(fileId);
  });

  it('should save and get file part', () => {
    const mockMessages = new MockMessages();
    const fileId = bigInt(123);
    const data = Buffer.from('hello');
    mockMessages.saveFilePart(fileId, 0, data);
    const parts = mockMessages.getFile(fileId);
    expect(Object.keys(parts).length).toEqual(1);
    expect(parts[0]).toEqual(data);
  });

  it('should edit a message', () => {
    const mockMessages = new MockMessages();
    const messageId = mockMessages.sendMessage({ message: 'hello' });
    mockMessages.editMessage(messageId, { message: 'world' });
    const message = mockMessages.getMessage(messageId);
    expect(message.text).toEqual('world');
  });

  it('should edit a message with file', () => {
    const mockMessages = new MockMessages();
    const fileId = bigInt(123);
    const messageId = mockMessages.sendMessage({ file: fileId });
    const fileId2 = bigInt(456);
    mockMessages.editMessage(messageId, { file: fileId2 });
    const message = mockMessages.getMessage(messageId);
    expect(message.document.id).toEqual(fileId2);
  });
});
