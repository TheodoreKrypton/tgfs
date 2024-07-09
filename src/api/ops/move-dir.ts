import { Client } from 'src/api';

import { copyDir } from './copy-dir';

export const moveDir =
  (client: Client) => async (pathFrom: string, pathTo: string) => {
    const { from, to } = await copyDir(client)(pathFrom, pathTo);

    await client.dir.rmDangerously(from);
  };
