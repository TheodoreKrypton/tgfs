import { FileOrDirectoryAlreadyExistsError } from 'src/errors/path';

import { TGFSDirectorySerialized, TGFSFileRefSerialized } from './message';

export class TGFSFileRef {
  constructor(
    private messageId: number,
    public name: string,
    private location: TGFSDirectory,
  ) { }

  public toObject(): TGFSFileRefSerialized {
    return { type: 'FR', messageId: this.messageId, name: this.name };
  }

  public delete() {
    this.location.deleteFile(this);
  }

  public getLocation() {
    return this.location;
  }

  public getMessageId() {
    return this.messageId;
  }

  public setMessageId(messageId: number) {
    this.messageId = messageId;
  }
}

export class TGFSDirectory {
  constructor(
    public name: string,
    private parent: TGFSDirectory,
    private children: TGFSDirectory[] = [],
    private files: TGFSFileRef[] = [],
  ) { }

  public toObject(): TGFSDirectorySerialized {
    const children = [];
    this.children.forEach((child) => {
      children.push(child.toObject());
    });
    return {
      type: 'D',
      name: this.name,
      children,
      files: this.files ? this.files.map((f) => f.toObject()) : [],
    };
  }

  public static fromObject(
    obj: TGFSDirectorySerialized,
    parent?: TGFSDirectory,
  ): TGFSDirectory {
    const children = [];
    const dir = new TGFSDirectory(obj.name, parent, children);

    dir.files = obj.files
      ? obj.files
        .filter((file) => {
          return file.name && file.messageId;
        })
        .map((file) => {
          return new TGFSFileRef(file.messageId, file.name, dir);
        })
      : [];

    obj.children.forEach((child) => {
      children.push(TGFSDirectory.fromObject(child, dir));
    });
    return dir;
  }

  public createDir(name: string, dir?: TGFSDirectory) {
    if (this.findDirs([name]).length) {
      throw new FileOrDirectoryAlreadyExistsError(name);
    }
    const child = dir
      ? new TGFSDirectory(name, this, dir.children, dir.files)
      : new TGFSDirectory(name, this);
    this.children.push(child);
    return child;
  }

  public findDirs(names?: string[]): Array<TGFSDirectory> {
    if (!names) {
      return this.children;
    } else {
      const namesSet = new Set(names);
      return this.children.filter((child) => namesSet.has(child.name));
    }
  }

  public findDir(name: string): TGFSDirectory {
    return this.findDirs([name])[0];
  }

  public findFiles(names?: string[]): Array<TGFSFileRef> {
    if (!names) {
      return this.files;
    } else {
      const namesSet = new Set(names);
      return this.files.filter((child) => namesSet.has(child.name));
    }
  }

  public findFile(name: string): TGFSFileRef {
    return this.findFiles([name])[0];
  }

  public createFileRef(name: string, fileMessageId: number): TGFSFileRef {
    if (this.findFile(name)) {
      throw new FileOrDirectoryAlreadyExistsError(name);
    }
    const fr = new TGFSFileRef(fileMessageId, name, this);
    this.files.push(fr);
    return fr;
  }

  public deleteFile(fr: TGFSFileRef) {
    this.files = this.files.filter((file) => file !== fr);
  }

  public delete() {
    if (this.parent) {
      this.parent.children = this.parent.children.filter(
        (child) => child !== this,
      );
    } else {
      // root directory
      this.children = [];
      this.files = [];
    }
  }
}
