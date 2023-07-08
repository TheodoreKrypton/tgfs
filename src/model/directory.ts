import { TGFSDirectoryObject, TGFSFileRefObject } from './message';

export class TGFSFileRef {
  constructor(
    public messageId: number,
    public name: string,
    public location: TGFSDirectory,
  ) {}

  public toObject(): TGFSFileRefObject {
    return { type: 'FR', messageId: this.messageId, name: this.name };
  }
}

export class TGFSDirectory {
  constructor(
    public name: string,
    public parent: TGFSDirectory,
    public children: TGFSDirectory[],
    public files: TGFSFileRef[] = [],
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
}
