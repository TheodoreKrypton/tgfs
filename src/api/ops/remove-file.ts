import { FileOrDirectoryDoesNotExistError } from '../../errors/path';
import { Client } from '../client';
import { navigateToDir } from './navigate-to-dir';
import { splitPath } from './utils';

export const removeFile = (client: Client) => async (path: string) => {
  const [basePath, name] = splitPath(path);
  const dir = await navigateToDir(client)(basePath);
  const fileRef = dir.findFiles([name])[0];
  if (fileRef) {
    await client.deleteFile(fileRef);
  } else {
    throw new FileOrDirectoryDoesNotExistError(path);
  }
};
