import { Client } from '../api';
import { FileOrDirectoryDoesNotExistError } from '../errors/path';
import { navigateToDir } from './navigate-to-dir';
import { splitPath } from './utils';

export const rm =
  (client: Client) => async (argv: { path: string; recursive?: boolean }) => {
    const { path, recursive } = argv;
    const [basePath, name] = splitPath(path);
    const dir = await navigateToDir(client)(basePath);
    if (!recursive) {
      const fileRef = dir.findFiles([name])[0];
      const child = dir.findChildren([name])[0];
      console.log(fileRef);
      if (fileRef) {
        await client.deleteFileAtVersion(fileRef);
      } else if (child) {
        await client.deleteEmptyDirectory(child);
      } else {
        throw new FileOrDirectoryDoesNotExistError(path);
      }
    } else {
      const nextDir = name ? dir.findChildren([name])[0] : dir;
      await client.deleteDirectory(nextDir);
    }
    return `removed ${path}`;
  };
