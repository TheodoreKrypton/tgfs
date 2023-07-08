import { Api } from 'telegram';
import { v4 as uuid } from 'uuid';

import { TGFSFileObject, TGFSFileVersionObject } from './message';

export class TGFSFileVersion {
  id: string;
  updatedAt: Date;
  messageId: number;

  toObject(): TGFSFileVersionObject {
    return {
      type: 'FV',
      id: this.id,
      updatedAt: this.updatedAt.getTime(),
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

  static fromObject(
    tgfsFileVersionObject: TGFSFileVersionObject,
  ): TGFSFileVersion {
    const tgfsFileVersion = new TGFSFileVersion();
    tgfsFileVersion.id = tgfsFileVersionObject['id'];
    tgfsFileVersion.updatedAt = new Date(tgfsFileVersionObject['updatedAt']);
    tgfsFileVersion.messageId = tgfsFileVersionObject['messageId'];
    return tgfsFileVersion;
  }
}

export class TGFSFile {
  versions: { [key: string]: TGFSFileVersion } = {};
  latestVersionId: string;

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
    tgfsFile.latestVersionId = tgfsFileObject.versions.reduce((a, b) => {
      return a.updatedAt > b.updatedAt ? a : b;
    }).id;
    tgfsFileObject.versions.forEach((version: TGFSFileVersionObject) => {
      tgfsFile.versions[version.id] = TGFSFileVersion.fromObject(version);
    });

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

  addVersionFromFileMessage(message: Api.Message) {
    const version = TGFSFileVersion.fromFileMessage(message);
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
}
