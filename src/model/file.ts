import { Api } from 'telegram';

export class TGFSFileVersion {
  constructor(
    public readonly id: string,
    public readonly uploadedAt: string,
    public readonly md5: string,
  ) {}
}

export class TGFSFile {
  versions: TGFSFileVersion[];

  constructor(public readonly name: string) {}

  getLatest(): Api.MessageMediaDocument {
    return null;
  }

  getVersion(id: string): Api.MessageMediaDocument {
    return null;
  }
}
