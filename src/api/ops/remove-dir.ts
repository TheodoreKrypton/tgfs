import { FileOrDirectoryDoesNotExistError } from '../../errors/path';
import { Client } from '../client';
import { navigateToDir } from './navigate-to-dir';
import { splitPath } from './utils';

export const removeDir =
  (client: Client) => async (path: string, recursive: boolean) => {
    const [basePath, name] = splitPath(path);
    const dir = await navigateToDir(client)(basePath);
    if (!recursive) {
      const child = dir.findChildren([name])[0];
      if (child) {
        await client.deleteEmptyDirectory(child);
      } else {
        throw new FileOrDirectoryDoesNotExistError(path);
      }
    } else {
      const nextDir = name ? dir.findChildren([name])[0] : dir;
      await client.dangerouslyDeleteDirectory(nextDir);
    }
  };
