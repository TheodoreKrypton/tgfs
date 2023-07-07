import { Api } from 'telegram';
import { v4 as uuid } from 'uuid';

export class TGFSFileVersion {
  id: string;
  updatedAt: Date;
  messageId: number;

  toObject(): object {
    return {
      type: 'TGFSFileVersion',
      id: this.id,
      updatedAt: this.updatedAt,
      messageId: this.messageId,
    };
  }

  static fromFileMessage(message: Api.Message): TGFSFileVersion {
    const tgfsFileVersion = new TGFSFileVersion();
    tgfsFileVersion.id = uuid();
    tgfsFileVersion.updatedAt = new Date();
    tgfsFileVersion.messageId = message.id;
    return tgfsFileVersion;
  }

  static fromObject(tgfsFileVersionObject: TGFSFileVersion): TGFSFileVersion {
    const tgfsFileVersion = new TGFSFileVersion();
    tgfsFileVersion.id = tgfsFileVersionObject['id'];
    tgfsFileVersion.updatedAt = tgfsFileVersionObject['updatedAt'];
    tgfsFileVersion.messageId = tgfsFileVersionObject['messageId'];
    return tgfsFileVersion;
  }
}

export class TGFSFile {
  versions: Map<string, TGFSFileVersion> = new Map();
  latestVersionId: string;

  constructor(public readonly name: string) {}

  toObject(): object {
    return {
      type: 'TGFSFile',
      name: this.name,
      versions: Array.from(this.versions.values())
        .sort((a, b) => {
          return a.updatedAt.getTime() - b.updatedAt.getTime();
        })
        .map((version) => version.toObject()),
    };
  }

  static fromObject(tgfsFileObject: object): TGFSFile {
    const tgfsFile = new TGFSFile(tgfsFileObject['name']);
    tgfsFile.latestVersionId = tgfsFileObject['versions'].reduce(
      (a: TGFSFileVersion, b: TGFSFileVersion) => {
        return a.updatedAt.getTime() > b.updatedAt.getTime() ? a : b;
      },
    ).id;
    tgfsFileObject['versions'].forEach((version: TGFSFileVersion) => {
      tgfsFile.versions.set(version.id, TGFSFileVersion.fromObject(version));
    });

    return tgfsFile;
  }

  getLatest(): TGFSFileVersion {
    return this.getVersion(this.latestVersionId);
  }

  getVersion(uuid: string): TGFSFileVersion {
    return this.versions.get(uuid);
  }

  addVersion(version: TGFSFileVersion) {
    this.versions.set(version.id, version);
  }

  addVersionFromFileMessage(message: Api.Message) {
    const version = TGFSFileVersion.fromFileMessage(message);
    this.addVersion(version);
    this.latestVersionId = version.id;
  }

  updateVersion(version: TGFSFileVersion) {
    this.versions.set(version.id, version);
  }
}
