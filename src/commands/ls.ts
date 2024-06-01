import { PathLike } from 'fs';

import { Client } from 'src/api';
import { list } from 'src/api/ops';
import { TGFSDirectory, TGFSFileRef } from 'src/model/directory';

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
    const fd = await client.getFileDesc(res);
    return fileInfo(client, fd);
  }
};
