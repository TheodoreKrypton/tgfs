import { RelativePathError } from 'src/errors/path';

import { Client } from '../api';
import { navigateToDir } from './navigate-to-dir';
import { splitPath } from './utils';

export const mkdir =
  (client: Client) => async (args: { path: string; parents?: boolean }) => {
    const { path, parents } = args;

    if (!parents) {
      const [basePath, name] = splitPath(path);
      const dir = await navigateToDir(client)(basePath);
      await client.createDirectoryUnder(name, dir);
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

        const dir = await client.createDirectoryUnder(p, currentDir);
        currentDir = dir;
      }
    }
    return `created ${path}`;
  };
