import { Client } from '../api';
import { navigateToDir } from './navigate-to-dir';

export const mkdir = (client: Client) => async (path: string) => {
  const parts = path.toString().split('/');
  const dir = await navigateToDir(client)(
    parts.slice(0, parts.length - 1).join('/'),
  );

  await client.createDirectoryUnder(parts[parts.length - 1], dir);

  return `created ${path}`;
};
