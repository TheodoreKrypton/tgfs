import * as fs from 'fs';

import { Client } from '../api';
import { FileOrDirectoryDoesNotExistError } from '../errors/path';
import { fileInfo } from './ls';
import { navigateToDir } from './navigate-to-dir';
import { splitPath } from './utils';

export const cp =
  (client: Client) =>
  async (argv: { local: fs.PathLike; remote: fs.PathLike }) => {
    const { local, remote } = argv;
    let [basePath, name] = splitPath(remote);
    name = name || local.toString().split('/').pop(); // use the local file name if the name is not specified

    const dir = await navigateToDir(client)(basePath);

    if (!fs.existsSync(local.toString())) {
      throw new FileOrDirectoryDoesNotExistError(local.toString());
    }

    const created = await client.putFileUnder(name, dir, local.toString());

    return `File created ${basePath}/${name}\n${await fileInfo(
      client,
      created,
    )}`;
  };
