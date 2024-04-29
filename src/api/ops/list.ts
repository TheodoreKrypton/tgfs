import { PathLike } from 'fs';

import { Client } from 'src/api';
import { FileOrDirectoryDoesNotExistError } from 'src/errors/path';
import { TGFSDirectory, TGFSFileRef } from 'src/model/directory';

import { navigateToDir } from './navigate-to-dir';
import { splitPath } from './utils';

export const list =
  (client: Client) =>
  async (
    path: PathLike,
  ): Promise<TGFSFileRef | Array<TGFSFileRef | TGFSDirectory>> => {
    const [basePath, name] = splitPath(path);
    const dir = await navigateToDir(client)(basePath);

    let nextDir = dir;

    if (name) {
      nextDir = dir.findChildren([name])[0];
    }
    if (nextDir) {
      return [...nextDir.findChildren(), ...nextDir.findFiles()];
    } else {
      const nextFile = dir.findFiles([name])[0];
      if (nextFile) {
        return nextFile;
      } else {
        const pathStr = path.toString();
        throw new FileOrDirectoryDoesNotExistError(pathStr, `list ${pathStr}`);
      }
    }
  };
