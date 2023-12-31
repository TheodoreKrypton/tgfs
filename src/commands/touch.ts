import * as fs from 'fs';

import { Client } from 'src/api';
import { createEmptyFile } from 'src/api/ops/create-empty-file';

import { fileInfo } from './utils';

export const touch = (client: Client) => async (argv: { path: string }) => {
  const { path } = argv;

  if (!fs.existsSync(path)) {
    const created = await createEmptyFile(client)(path);

    return `File created ${path}\n${await fileInfo(client, created)}`;
  }
};
