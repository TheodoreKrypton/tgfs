import { BusinessError } from './base';

export abstract class TelegramError extends BusinessError {}

export class FileTooBig extends TelegramError {
  constructor(size: number) {
    const message = `File size ${size} exceeds Telegram limit`;
    super(message, 'FILE_TOO_BIG', message);
  }
}

export class MessageNotFound extends TelegramError {
  constructor(messageId: number) {
    const message = `Message with id ${messageId} not found`;
    super(message, 'MESSAGE_NOT_FOUND', message);
  }
}