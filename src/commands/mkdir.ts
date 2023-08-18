import { Client } from 'src/api';
import { createDir } from 'src/api/ops';

export const mkdir =
  (client: Client) => async (args: { path: string; parents?: boolean }) => {
    const { path, parents } = args;
    await createDir(client)(path, parents ?? false);
    return `created ${path}`;
  };
