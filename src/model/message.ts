export class TGFSFileVersionSerialized {
  type: 'FV';
  id: string;
  updatedAt: number;
  messageId: number;
  size: number;
}

export class TGFSFileObject {
  type: 'F';
  name: string;
  versions: TGFSFileVersionSerialized[];
}

export class TGFSFileRefSerialized {
  type: 'FR';
  messageId: number;
  name: string;
}

export class TGFSDirectorySerialized {
  type: 'D';
  name: string;
  children: TGFSDirectorySerialized[];
  files: TGFSFileRefSerialized[];
}
