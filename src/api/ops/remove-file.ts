import { Client } from 'src/api';
import { FileOrDirectoryDoesNotExistError } from 'src/errors/path';

import { navigateToDir } from './navigate-to-dir';
import { splitPath } from './utils';

export const removeFile = (client: Client) => async (path: string) => {
  const [basePath, name] = splitPath(path);
  const dir = navigateToDir(client)(basePath);
  const fileRef = dir.findFiles([name])[0];
  if (fileRef) {
    await client.file.rm(fileRef);
  } else {
    throw new FileOrDirectoryDoesNotExistError(path, `remove file ${path}`);
  }
};
