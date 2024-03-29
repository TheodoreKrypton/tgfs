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

export type SaveFilePartReq = {
  fileId: BigInteger;
  bytes: Buffer;
};

export type SaveBigFilePartReq = SaveFilePartReq & {
  filePart: number;
  fileTotalParts: number;
};

export type SaveFilePartResp = {
  success: boolean;
};

export type UploadedFile = {
  id: BigInteger;
  parts: number;
  name: string;
};

export type FileAttr = {
  name?: string;
  caption?: string;
};

export type SendFileReq = Chat &
  FileAttr & {
    file: UploadedFile;
  };

export type EditMessageMediaReq = Chat &
  Message &
  FileAttr & {
    buffer: Buffer;
  };

export type DownloadFileReq = Chat &
  Message & {
    chunkSize: number;
  };

export type DownloadFileResp = AsyncGenerator<Buffer>;
