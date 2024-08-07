import { Client } from 'src/api';
import { RelativePathError } from 'src/errors/path';
import { Logger } from 'src/utils/logger';

import { navigateToDir } from './navigate-to-dir';
import { splitPath } from './utils';

export const createDir =
  (client: Client) => async (path: string, parents: boolean) => {
    Logger.info(`Creating directory ${path}`);
    if (!parents) {
      const [basePath, name] = splitPath(path);
      const dir = navigateToDir(client)(basePath);
      return await client.dir.create({ name: name, under: dir });
    } else {
      if (!path.startsWith('/')) {
        throw new RelativePathError(path);
      }

      const paths = path.split('/').filter((p) => p);
      let currentDir = client.dir.root();
      for (const p of paths) {
        const children = currentDir.findDirs([p]);
        if (children.length > 0) {
          currentDir = children[0];
          continue;
        }

        const dir = await client.dir.create({
          name: p,
          under: currentDir,
        });
        currentDir = dir;
      }

      return currentDir;
    }
  };
