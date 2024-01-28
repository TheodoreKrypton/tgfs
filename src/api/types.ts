import { BigInteger } from 'big-integer';

export type Message = {
  messageId: number;
};

export type Chat = {
  chatId: number;
};

export type GetMessagesReq = Chat & {
  messageIds: number[];
};

export type MessageResp = Message & {
  text?: string;
  document?: {
    size: BigInteger;
    id: BigInteger;
    accessHash: BigInteger;
    fileReference: Buffer;
  };
};

export type GetMessagesResp = MessageResp[];

export type SearchMessagesReq = Chat & {
  search: string;
};

export type GetPinnedMessagesReq = Chat & {};

export type SendMessageResp = Message & {};

export type SendTextReq = Chat & {
  text: string;
};

export type EditMessageTextReq = Chat & Message & SendTextReq;

export type PinMessageReq = Chat & Message;

export type SaveBigFilePartReq = {
  fileId: BigInteger;
  filePart: number;
  fileTotalParts: number;
  bytes: Buffer;
};

export type SaveBigFilePartResp = {
  success: boolean;
};

export type BigFile = {
  id: BigInteger;
  parts: number;
  name: string;
};

export type SendFileReq = Chat & {
  name?: string;
};

export type SendBigFileReq = SendFileReq & {
  file: BigFile;
};

export type SendFileFromPathReq = SendFileReq & {
  filePath: string;
};

export type SendFileFromBufferReq = SendFileReq & {
  buffer: Buffer;
};

export type EditMessageMediaReq = Message & SendFileFromBufferReq;

export type DownloadFileReq = Chat &
  Message & {
    chunkSize: number;
  };

export type DownloadFileResp = AsyncGenerator<Buffer>;
