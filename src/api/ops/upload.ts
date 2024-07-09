import * as fs from 'fs';
import { Readable } from 'stream';

import { Client } from 'src/api';
import { FileOrDirectoryDoesNotExistError } from 'src/errors/path';

import { navigateToDir } from './navigate-to-dir';
import { splitPath } from './utils';

export const uploadFromLocal =
  (client: Client) => async (local: fs.PathLike, remote: fs.PathLike) => {
    let [basePath, name] = splitPath(remote);

    const dir = navigateToDir(client)(basePath);

    if (!fs.existsSync(local.toString())) {
      const path = local.toString();
      throw new FileOrDirectoryDoesNotExistError(path, `upload from ${path}`);
    }

    return await client.file.upload(
      { under: dir },
      { name, path: local.toString() },
    );
  };

export const uploadFromBytes =
  (client: Client) => async (bytes: Buffer, remote: fs.PathLike) => {
    let [basePath, name] = splitPath(remote);

    const dir = navigateToDir(client)(basePath);

    return await client.file.upload({ under: dir }, { name, buffer: bytes });
  };

export const uploadFromStream =
  (client: Client) =>
  async (stream: Readable, size: number, remote: fs.PathLike) => {
    let [basePath, name] = splitPath(remote);

    const dir = navigateToDir(client)(basePath);

    return await client.file.upload({ under: dir }, { name, stream, size });
  };
