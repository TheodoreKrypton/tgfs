import * as fs from 'fs';

import { Client } from 'src/api';
import { upload } from 'src/api/ops';
import { splitPath } from 'src/api/ops/utils';

import { fileInfo } from './utils';

export const cp =
  (client: Client) =>
  async (argv: { local: fs.PathLike; remote: fs.PathLike }) => {
    const { local, remote } = argv;

    let [basePath, name] = splitPath(remote);
    name = name || local.toString().split('/').pop(); // use the local file name if the name is not specified
    const remotePath = `${basePath}/${name}`;

    const created = await upload(client)(local, remotePath);

    return `File created ${remotePath}\n${await fileInfo(client, created)}`;
  };
