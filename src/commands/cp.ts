import { PathLike } from 'fs';

import { Client } from '../api';
import { fileInfo } from './ls';
import { navigateToDir } from './navigate-to-dir';
import { splitPath } from './utils';

export const cp =
  (client: Client) => async (local: PathLike, remote: PathLike) => {
    let [basePath, name] = splitPath(remote);
    name = name || local.toString().split('/').pop(); // use the local file name if the name is not specified
    
    const dir = await navigateToDir(client)(basePath);

    const created = await client.putFileUnder(name, dir, local.toString());

    return `File created ${basePath}/${name}\n${await fileInfo(
      client,
      created,
    )}`;
  };
