import { PathLike } from 'fs';

import { Client } from '../api';
import { list } from '../api/ops/list';
import { TGFSDirectory, TGFSFileRef } from '../model/directory';
import { fileInfo } from './utils';

export const ls = (client: Client) => async (argv: { path: PathLike }) => {
  const { path } = argv;
  const res = await list(client)(path);
  if (Array.isArray(res)) {
    return res
      .map((item: TGFSDirectory | TGFSFileRef) => {
        return item.name;
      })
      .join('  ');
  } else {
    return fileInfo(client, res);
  }
};
