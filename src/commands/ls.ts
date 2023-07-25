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

export const ls = (client: Client) => async (argv: { path: PathLike }) => {
  const { path } = argv;
  const [basePath, name] = splitPath(path);
  const dir = await navigateToDir(client)(basePath);

  let nextDir = dir;

  if (name) {
    nextDir = dir.findChildren([name])[0];
  }
  if (nextDir) {
    return nextDir
      .findChildren()
      .map((c) => c.name)
      .concat(dir.findFiles().map((f) => f.name))
      .join(' ');
  } else {
    const nextFile = dir.findFiles([name])[0];
    if (nextFile) {
      return fileInfo(client, nextFile);
    } else {
      throw new FileOrDirectoryDoesNotExistError(path.toString());
    }
  }
};
