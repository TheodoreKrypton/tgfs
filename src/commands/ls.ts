import { PathLike } from 'fs';

import { Client } from '../api';
import { FileOrDirectoryDoesNotExistError } from '../errors/directory';
import { TGFSFileRef } from '../model/directory';
import { navigateToDir } from './navigate-to-dir';

const fileInfo = async (client: Client, fileRef: TGFSFileRef) => {
  const info = await client.getFileInfo(fileRef);
  const head = `${info.name}, ${Object.keys(info.versions).length} versions`;
  const versions = Object.entries(info.versions).map(([id, version]) => {
    return `${id}: updated at ${version.updatedAt}`;
  });
  return [head, ...versions].join('\n');
};

export const ls = (client: Client) => async (path: PathLike) => {
  const parts = path
    .toString()
    .split('/')
    .filter((part) => part !== '');
  let dir = await navigateToDir(client)(
    parts.slice(0, parts.length - 1).join('/'),
  );

  let nextDir = dir;

  if (parts.length > 0) {
    nextDir = dir.children.find((d) => d.name === parts[parts.length - 1]);
  }
  if (nextDir) {
    return nextDir.children
      .map((c) => c.name)
      .concat(dir.files?.map((f) => f.name))
      .join(' ');
  } else {
    const nextFile = dir.files?.find((f) => f.name === parts[parts.length - 1]);
    if (nextFile) {
      return fileInfo(client, nextFile);
    } else {
      throw new FileOrDirectoryDoesNotExistError(path.toString());
    }
  }
};
