export type FileTags = {
  sha256: string;
};

export type FileMessage = {
  name?: string;
  tags?: FileTags;
  caption?: string;
};

export type FileMessageFromPath = FileMessage & {
  path: string;
};

export type FileMessageFromBuffer = FileMessage & {
  buffer: Buffer;
};

export type GeneralFileMessage = FileMessageFromPath | FileMessageFromBuffer;
