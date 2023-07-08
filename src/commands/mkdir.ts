import { Client } from '../api';
import { navigateToDir } from './navigate-to-dir';
import { splitPath } from './utils';

export const mkdir = (client: Client) => async (path: string) => {
  const [basePath, name] = splitPath(path);

  const dir = await navigateToDir(client)(basePath);

  await client.createDirectoryUnder(name, dir);

  return `created ${path}`;
};
