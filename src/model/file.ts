import { v4 as uuid } from 'uuid';

import { TGFSFileObject, TGFSFileVersionSerialized } from './message';

export class TGFSFileVersion {
  static EMPTY_FILE = -1;

  id: string;
  updatedAt: Date;
  messageId: number;
  size: number;

  toObject(): TGFSFileVersionSerialized {
    return {
      type: 'FV',
      id: this.id,
      updatedAt: this.updatedAt.getTime(),
      messageId: this.messageId,
    };
  }

  static empty(): TGFSFileVersion {
    const tgfsFileVersion = new TGFSFileVersion();
    tgfsFileVersion.id = uuid();
    tgfsFileVersion.updatedAt = new Date();
    tgfsFileVersion.setInvalid();
    return tgfsFileVersion;
  }

  static fromFileMessageId(fileMessageId: number): TGFSFileVersion {
    const tgfsFileVersion = new TGFSFileVersion();
    tgfsFileVersion.id = uuid();
    tgfsFileVersion.updatedAt = new Date();
    tgfsFileVersion.messageId = fileMessageId;
    return tgfsFileVersion;
  }

  static fromObject(
    tgfsFileVersionObject: TGFSFileVersionSerialized,
  ): TGFSFileVersion {
    const tgfsFileVersion = new TGFSFileVersion();
    tgfsFileVersion.id = tgfsFileVersionObject['id'];
    tgfsFileVersion.updatedAt = new Date(tgfsFileVersionObject['updatedAt']);
    tgfsFileVersion.messageId = tgfsFileVersionObject['messageId'];
    return tgfsFileVersion;
  }

  setInvalid() {
    this.messageId = TGFSFileVersion.EMPTY_FILE;
    this.size = 0;
  }
}

export class TGFSFile {
  versions: { [key: string]: TGFSFileVersion } = {};
  latestVersionId: string;
  createdAt: Date;

  constructor(public readonly name: string) {}

  toObject(): TGFSFileObject {
    return {
      type: 'F',
      name: this.name,
      versions: this.getVersionsSorted().map((version) => version.toObject()),
    };
  }

  static fromObject(tgfsFileObject: TGFSFileObject): TGFSFile {
    const tgfsFile = new TGFSFile(tgfsFileObject.name);
    let lastUpdatedAt = 0;
    tgfsFile.createdAt = new Date();

    for (const version of tgfsFileObject.versions) {
      tgfsFile.addVersion(TGFSFileVersion.fromObject(version));
      if (version.updatedAt > lastUpdatedAt) {
        lastUpdatedAt = version.updatedAt;
        tgfsFile.latestVersionId = version.id;
      }
      if (version.updatedAt < tgfsFile.createdAt.getTime()) {
        tgfsFile.createdAt = new Date(version.updatedAt);
      }
    }

    return tgfsFile;
  }

  static empty(name: string): TGFSFile {
    const tgfsFile = new TGFSFile(name);
    tgfsFile.createdAt = new Date();
    tgfsFile.addEmptyVersion();
    return tgfsFile;
  }

  getLatest(): TGFSFileVersion {
    return this.getVersion(this.latestVersionId);
  }

  getVersion(uuid: string): TGFSFileVersion {
    return this.versions[uuid];
  }

  addVersion(version: TGFSFileVersion) {
    this.versions[version.id] = version;
  }

  addEmptyVersion() {
    const version = TGFSFileVersion.empty();
    this.addVersion(version);
    this.latestVersionId = version.id;
  }

  addVersionFromFileMessageId(fileMessageId: number) {
    const version = TGFSFileVersion.fromFileMessageId(fileMessageId);
    this.addVersion(version);
    this.latestVersionId = version.id;
  }

  updateVersion(version: TGFSFileVersion) {
    this.versions[version.id] = version;
  }

  getVersionsSorted(): TGFSFileVersion[] {
    return Object.values(this.versions).sort((a, b) => {
      return a.updatedAt.getTime() - b.updatedAt.getTime();
    });
  }

  deleteVersion(uuid: string) {
    delete this.versions[uuid];
  }

  isEmptyFile(): boolean {
    return this.getLatest().messageId === TGFSFileVersion.EMPTY_FILE;
  }
}
