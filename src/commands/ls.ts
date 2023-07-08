import { PathLike } from 'fs';

import { Client } from '../api';
import { FileOrDirectoryDoesNotExistError } from '../errors/path';
import { TGFSFileRef } from '../model/directory';
import { navigateToDir } from './navigate-to-dir';
import { splitPath } from './utils';

export const fileInfo = async (client: Client, fileRef: TGFSFileRef) => {
  const info = await client.getFileInfo(fileRef);
  const head = `${info.name}, ${Object.keys(info.versions).length} versions`;
  const versions = info
    .getVersionsSorted()
    .reverse()
    .map((ver) => `${ver.id}: updated at ${ver.updatedAt}`);
  return [head, ...versions].join('\n');
};

export const ls = (client: Client) => async (path: PathLike) => {
  const [basePath, name] = splitPath(path);
  const dir = await navigateToDir(client)(basePath);

  let nextDir = dir;

  if (name) {
    nextDir = dir.children.find((d) => d.name === name);
  }
  if (nextDir) {
    return nextDir.children
      .map((c) => c.name)
      .concat(dir.files?.map((f) => f.name))
      .join(' ');
  } else {
    const nextFile = dir.files?.find((f) => f.name === name);
    if (nextFile) {
      return fileInfo(client, nextFile);
    } else {
      throw new FileOrDirectoryDoesNotExistError(path.toString());
    }
  }
};
