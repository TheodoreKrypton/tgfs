import { Client } from 'src/api';
import { removeDir, removeFile } from 'src/api/ops';
import { FileOrDirectoryDoesNotExistError } from 'src/errors/path';

export const rm =
  (client: Client) => async (argv: { path: string; recursive?: boolean }) => {
    const { path, recursive } = argv;
    try {
      await removeFile(client)(path);
    } catch (err) {
      if (err instanceof FileOrDirectoryDoesNotExistError) {
        await removeDir(client)(path, recursive ?? false);
      } else {
        throw err;
      }
    }
    return `removed ${path}`;
  };
