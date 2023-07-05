import { BigInteger } from 'big-integer';
import { Api } from 'telegram';
import { v4 as uuid } from 'uuid';

export class TGFSFileVersion {
  id: string;
  md5: string;
  updatedAt: Date;

  fileId: BigInteger;
  accessHash: BigInteger;
  fileRef: Buffer;

  async calculateMd5() {
    this.md5 = '';
  }

  getDocument(): Api.Document {
    return {
      id: this.fileId,
      accessHash: this.accessHash,
      fileReference: this.fileRef,
    } as Api.Document;
  }

  toObject(): object {
    return {
      id: this.id,
      md5: this.md5,
      updatedAt: this.updatedAt,
      fileId: this.fileId,
      accessHash: this.accessHash,
      fileRef: this.fileRef,
    };
  }

  static async fromDocument(document: Api.Document): Promise<TGFSFileVersion> {
    const tgfsFileVersion = new TGFSFileVersion();
    tgfsFileVersion.id = uuid();
    tgfsFileVersion.updatedAt = new Date();

    tgfsFileVersion.fileId = document.id;
    tgfsFileVersion.accessHash = document.accessHash;
    tgfsFileVersion.fileRef = document.fileReference;

    await tgfsFileVersion.calculateMd5();

    return tgfsFileVersion;
  }

  static fromObject(tgfsFileVersionObject: TGFSFileVersion): TGFSFileVersion {
    const tgfsFileVersion = new TGFSFileVersion();
    tgfsFileVersion.id = tgfsFileVersionObject['id'];
    tgfsFileVersion.md5 = tgfsFileVersionObject['md5'];
    tgfsFileVersion.updatedAt = tgfsFileVersionObject['updatedAt'];
    tgfsFileVersion.fileId = tgfsFileVersionObject['fileId'];
    tgfsFileVersion.accessHash = tgfsFileVersionObject['accessHash'];
    tgfsFileVersion.fileRef = Buffer.from(
      tgfsFileVersionObject['fileRef']['data'],
    );
    return tgfsFileVersion;
  }
}

export class TGFSFile {
  versions: Map<string, TGFSFileVersion> = new Map();
  latestVersionId: string;

  constructor(public readonly name: string) {}

  toObject(): object {
    return {
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

  getLatest(): Api.Document {
    return this.getVersion(this.latestVersionId);
  }

  getVersion(uuid: string): Api.Document {
    const version = this.versions.get(uuid);
    return version.getDocument();
  }

  addVersion(version: TGFSFileVersion) {
    this.versions.set(version.id, version);
  }
}
