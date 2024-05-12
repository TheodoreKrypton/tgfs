import { Client } from 'src/api';
import { FileOrDirectoryDoesNotExistError } from 'src/errors/path';

import { navigateToDir } from './navigate-to-dir';
import { splitPath } from './utils';

export const removeDir =
  (client: Client) => async (path: string, recursive: boolean) => {
    const [basePath, name] = splitPath(path);
    const dir = navigateToDir(client)(basePath);
    if (!recursive) {
      const child = dir.findChildren([name])[0];
      if (child) {
        await client.deleteEmptyDirectory(child);
      } else {
        throw new FileOrDirectoryDoesNotExistError(path, `remove dir ${path}`);
      }
    } else {
      const nextDir = name ? dir.findChildren([name])[0] : dir;
      await client.dangerouslyDeleteDirectory(nextDir);
    }
  };
