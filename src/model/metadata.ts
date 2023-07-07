import { TGFSDirectory } from './directory';

export class TGFSMetadata {
  dir: TGFSDirectory;
  msgId: number;

  static fromObject(object: object): TGFSMetadata {
    const metadata = new TGFSMetadata();

    metadata.dir = TGFSDirectory.fromObject(object['dir'], null);

    return metadata;
  }

  toObject() {
    return {
      type: 'TGFSMetadata',
      dir: this.dir.toObject(),
    };
  }

  syncWith(metadata: TGFSMetadata) {
    return null;
  }
}
