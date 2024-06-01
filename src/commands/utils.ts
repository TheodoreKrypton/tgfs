import { Client } from 'src/api';
import { TGFSFile } from 'src/model/file';

export const fileInfo = async (client: Client, fileDesc: TGFSFile) => {
  const head = `${fileDesc.name}, ${
    Object.keys(fileDesc.versions).length
  } versions`;
  const versions = fileDesc
    .getVersionsSorted()
    .reverse()
    .map((ver) => `${ver.id}: updated at ${ver.updatedAt}`);
  return [head, ...versions].join('\n');
};
