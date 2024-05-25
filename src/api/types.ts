import { BigInteger } from 'big-integer';

export type Message = {
  messageId: number;
};

export type SentFileMessage = Message & {
  size: bigInt.BigInteger;
};

export type Chat = {
  chatId: number;
};

export type GetMessagesReq = Chat & {
  messageIds: number[];
};

export type Document = {
  size: BigInteger;
  id: BigInteger;
  accessHash: BigInteger;
  fileReference: Buffer;
};

export type MessageResp = Message & {
  text?: string;
  document?: Document;
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
  filePart: number;
};

export type SaveBigFilePartReq = SaveFilePartReq & {
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
    file: UploadedFile;
  };

export type DownloadFileReq = Chat &
  Message & {
    chunkSize: number;
  };

export type DownloadFileResp = {
  chunks: AsyncGenerator<Buffer>;
  size: bigInt.BigInteger;
};
