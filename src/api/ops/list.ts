import { PathLike } from 'fs';

import { Client } from 'src/api';
import { TGFSDirectory, TGFSFileRef } from 'src/model/directory';

import { navigateToDir } from './navigate-to-dir';
import { splitPath } from './utils';

export const list =
  (client: Client) =>
  async (
    path: PathLike,
  ): Promise<TGFSFileRef | Array<TGFSFileRef | TGFSDirectory>> => {
    const [basePath, name] = splitPath(path);
    const dir = navigateToDir(client)(basePath);

    let nextDir = dir;

    if (name) {
      nextDir = dir.findDir(name);
    }
    if (nextDir) {
      return client.dir.ls(nextDir);
    } else {
      // cannot find a sub-directory with the given name, so assume it's a file
      return client.dir.ls(dir, name);
    }
  };
