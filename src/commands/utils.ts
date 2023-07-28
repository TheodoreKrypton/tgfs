import { Client } from '../api';
import { TGFSFileRef } from '../model/directory';

export const fileInfo = async (client: Client, fileRef: TGFSFileRef) => {
  const info = await client.getFileInfo(fileRef);
  const head = `${info.name}, ${Object.keys(info.versions).length} versions`;
  const versions = info
    .getVersionsSorted()
    .reverse()
    .map((ver) => `${ver.id}: updated at ${ver.updatedAt}`);
  return [head, ...versions].join('\n');
};
