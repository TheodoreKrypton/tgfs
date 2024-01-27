import { FileOrDirectoryAlreadyExistsError } from 'src/errors/path';

import { TGFSDirectoryObject, TGFSFileRefObject } from './message';

export class TGFSFileRef {
  constructor(
    private messageId: number,
    public name: string,
    private location: TGFSDirectory,
  ) {}

  public toObject(): TGFSFileRefObject {
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
}

export class TGFSDirectory {
  constructor(
    public name: string,
    private parent: TGFSDirectory,
    private children: TGFSDirectory[] = [],
    private files: TGFSFileRef[] = [],
  ) {}

  public toObject(): TGFSDirectoryObject {
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
    obj: TGFSDirectoryObject,
    parent?: TGFSDirectory,
  ): TGFSDirectory {
    const children = [];
    const dir = new TGFSDirectory(obj.name, parent, children);

    dir.files = obj.files
      ? obj.files.map((file) => {
          return new TGFSFileRef(file.messageId, file.name, dir);
        })
      : [];

    obj.children.forEach((child) => {
      children.push(TGFSDirectory.fromObject(child, dir));
    });
    return dir;
  }

  public createChild(name: string) {
    if (this.findChildren([name]).length) {
      throw new FileOrDirectoryAlreadyExistsError(name);
    }
    const child = new TGFSDirectory(name, this);
    this.children.push(child);
    return child;
  }

  public findChildren(names?: string[]) {
    if (!names) {
      return this.children;
    } else {
      const namesSet = new Set(names);
      return this.children.filter((child) => namesSet.has(child.name));
    }
  }

  public findFiles(names?: string[]) {
    if (!names) {
      return this.files;
    } else {
      const namesSet = new Set(names);
      return this.files.filter((child) => namesSet.has(child.name));
    }
  }

  public createFileRef(name: string, fileMessageId: number) {
    const fr = new TGFSFileRef(fileMessageId, name, this);
    if (this.findFiles([fr.name])[0]) {
      throw new FileOrDirectoryAlreadyExistsError(fr.name);
    }
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
