export class TGFSFileVersionObject {
  type: 'FV';
  id: string;
  updatedAt: number;
  messageId: number;
}

export class TGFSFileObject {
  type: 'F';
  name: string;
  versions: TGFSFileVersionObject[];
}

export class TGFSFileRefObject {
  type: 'FR';
  messageId: number;
  name: string;
}

export class TGFSDirectoryObject {
  type: 'D';
  name: string;
  children: TGFSDirectoryObject[];
  files: TGFSFileRefObject[];
}
