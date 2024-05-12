import { Client } from 'src/api';

import { copyFile } from './copy-file';

export const moveFile =
  (client: Client) => async (pathFrom: string, pathTo: string) => {
    const { from, to } = await copyFile(client)(pathFrom, pathTo);
    await client.deleteFile(from);
  };
