import { Client } from '../api';
import { navigateToDir } from './navigate-to-dir';
import { splitPath } from './utils';

export const rm =
  (client: Client) => async (path: string, recursive: boolean) => {
    const [basePath, name] = splitPath(path);
    const dir = await navigateToDir(client)(basePath);
    if (!recursive) {
      const fileRef = dir.files?.find((f) => f.name === name);
      await client.deleteFileAtVersion(fileRef);
    } else {
      const nextDir = name ? dir.children?.find((d) => d.name === name) : dir;
      await client.deleteDirectory(nextDir);
    }
    return `removed ${path}`;
  };
