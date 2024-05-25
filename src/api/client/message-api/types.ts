import { Readable } from 'stream';

import { Message } from 'src/api/types';

export type FileTags = {
  sha256: string;
};

export type FileMessage = {
  name: string;
  tags?: FileTags;
  caption?: string;
};

export type FileMessageEmpty = FileMessage & {
  empty: true;
};

export type FileMessageFromPath = FileMessage & {
  path: string;
};

export type FileMessageFromBuffer = FileMessage & {
  buffer: Buffer;
};

export type FileMessageFromStream = FileMessage & {
  stream: Readable;
  size: number;
};

export type GeneralFileMessage =
  | FileMessageEmpty
  | FileMessageFromPath
  | FileMessageFromBuffer
  | FileMessageFromStream;

export const isFileMessageEmpty = (
  msg: GeneralFileMessage,
): msg is FileMessageEmpty => {
  return msg && 'empty' in msg;
};
