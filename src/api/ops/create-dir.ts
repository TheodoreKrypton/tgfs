import { RelativePathError } from '../../errors/path';
import { Client } from '../client';
import { navigateToDir } from './navigate-to-dir';
import { splitPath } from './utils';

export const createDir =
  (client: Client) => async (path: string, parents: boolean) => {
    if (!parents) {
      const [basePath, name] = splitPath(path);
      const dir = await navigateToDir(client)(basePath);
      return await client.createDirectory({ name: name, under: dir });
    } else {
      if (!path.startsWith('/')) {
        throw new RelativePathError(path);
      }

      const paths = path.split('/').filter((p) => p);
      let currentDir = client.getRootDirectory();
      for (const p of paths) {
        const children = currentDir.findChildren([p]);
        if (children.length > 0) {
          currentDir = children[0];
          continue;
        }

        const dir = await client.createDirectory({
          name: p,
          under: currentDir,
        });
        currentDir = dir;
      }

      return currentDir;
    }
  };
