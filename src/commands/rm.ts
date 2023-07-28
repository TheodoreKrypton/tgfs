import { Client } from '../api';
import { removeDir } from '../api/ops/remove-dir';
import { removeFile } from '../api/ops/remove-file';
import { FileOrDirectoryDoesNotExistError } from '../errors/path';

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
