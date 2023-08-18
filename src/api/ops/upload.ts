import * as fs from 'fs';

import { FileOrDirectoryDoesNotExistError } from '../../errors/path';
import { Client } from '../client';
import { navigateToDir } from './navigate-to-dir';
import { splitPath } from './utils';

export const upload =
  (client: Client) => async (local: fs.PathLike, remote: fs.PathLike) => {
    let [basePath, name] = splitPath(remote);

    const dir = await navigateToDir(client)(basePath);

    if (!fs.existsSync(local.toString())) {
      throw new FileOrDirectoryDoesNotExistError(local.toString());
    }

    return await client.uploadFile({ name, under: dir }, local.toString());
  };

export const uploadBytes =
  (client: Client) => async (bytes: Buffer, remote: fs.PathLike) => {
    let [basePath, name] = splitPath(remote);

    const dir = await navigateToDir(client)(basePath);

    return await client.uploadFile({ name, under: dir }, bytes);
  };

// TODO: upload stream
