export class TGFSFileRef {
  constructor(
    public readonly messageId: number,
    public readonly name: string,
    public readonly location: TGFSDirectory,
  ) {}

  public toObject(): object {
    return { type: 'TGFSFileRef', messageId: this.messageId, name: this.name };
  }
}

export class TGFSDirectory {
  files: TGFSFileRef[];

  constructor(
    public readonly name: string,
    public readonly parent: TGFSDirectory,
    public readonly children: TGFSDirectory[],
  ) {}

  public toObject(): object {
    const children = [];
    this.children.forEach((child) => {
      children.push(child.toObject());
    });
    return {
      type: 'TGFSDirectory',
      name: this.name,
      children,
      files: this.files ? this.files.map((f) => f.toObject()) : [],
    };
  }

  public static fromObject(
    obj: TGFSDirectory,
    parent?: TGFSDirectory,
  ): TGFSDirectory {
    const children = [];
    const dir = new TGFSDirectory(obj.name, parent, children);

    dir.files = obj.files
      ? obj.files.map((file) => {
          return new TGFSFileRef(file.messageId, file.name, dir);
        })
      : [];

    obj.children.forEach((child: TGFSDirectory) => {
      children.push(TGFSDirectory.fromObject(child, dir));
    });
    return dir;
  }
}
