import { Client } from '../api';
import { TGFSFileRef } from '../model/directory';

export const fileInfo = async (client: Client, fileRef: TGFSFileRef) => {
  const fileDesc = await client.getFileDesc(fileRef);
  const head = `${fileDesc.name}, ${
    Object.keys(fileDesc.versions).length
  } versions`;
  const versions = fileDesc
    .getVersionsSorted()
    .reverse()
    .map((ver) => `${ver.id}: updated at ${ver.updatedAt}`);
  return [head, ...versions].join('\n');
};
