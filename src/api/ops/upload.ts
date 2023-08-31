import * as fs from 'fs';

import { Client } from 'src/api';
import { FileOrDirectoryDoesNotExistError } from 'src/errors/path';

import { navigateToDir } from './navigate-to-dir';
import { splitPath } from './utils';

export const uploadFromLocal =
  (client: Client) => async (local: fs.PathLike, remote: fs.PathLike) => {
    let [basePath, name] = splitPath(remote);

    const dir = await navigateToDir(client)(basePath);

    if (!fs.existsSync(local.toString())) {
      throw new FileOrDirectoryDoesNotExistError(local.toString());
    }

    return await client.uploadFile({ name, under: dir }, local.toString());
  };

export const uploadFromBytes =
  (client: Client) => async (bytes: Buffer, remote: fs.PathLike) => {
    let [basePath, name] = splitPath(remote);

    const dir = await navigateToDir(client)(basePath);

    return await client.uploadFile({ name, under: dir }, bytes);
  };

// TODO: upload stream
