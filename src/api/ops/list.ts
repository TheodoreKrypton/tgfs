import { PathLike } from 'fs';

import { FileOrDirectoryDoesNotExistError } from '../../errors/path';
import { Client } from '../client';
import { navigateToDir } from './navigate-to-dir';
import { splitPath } from './utils';

export const list = (client: Client) => async (path: PathLike) => {
  const [basePath, name] = splitPath(path);
  const dir = await navigateToDir(client)(basePath);

  let nextDir = dir;

  if (name) {
    nextDir = dir.findChildren([name])[0];
  }
  if (nextDir) {
    return [...nextDir.findChildren(), ...dir.findFiles()];
  } else {
    const nextFile = dir.findFiles([name])[0];
    if (nextFile) {
      return nextFile;
    } else {
      throw new FileOrDirectoryDoesNotExistError(path.toString());
    }
  }
};