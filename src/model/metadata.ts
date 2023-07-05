import { TGFSDirectory } from './directory';

export class TGFSMetadata {
  dir: TGFSDirectory;
  msgId: number;

  static fromMetadataString(metadataString: string) {
    const metadata = new TGFSMetadata();
    const metadataObj = JSON.parse(metadataString) as TGFSMetadata;

    metadata.dir = TGFSDirectory.fromObject(metadataObj.dir, null);

    return metadata;
  }

  toMetadataString() {
    return JSON.stringify({ dir: this.dir.toObject() });
  }
}
