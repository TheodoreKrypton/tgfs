import { PathLike, existsSync } from 'fs';

import { Client } from '../client';
import { navigateToDir } from './navigate-to-dir';
import { splitPath } from './utils';

export const createEmptyFile = (client: Client) => async (path: PathLike) => {
  let [basePath, name] = splitPath(path);

  const dir = navigateToDir(client)(basePath);

  if (!existsSync(path)) {
    return await client.file.upload({ under: dir }, { name, empty: true });
  }
};
