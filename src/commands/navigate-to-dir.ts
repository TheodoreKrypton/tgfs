import { TGFSDirectory } from 'src/model/directory';

import { Client } from '../api';
import { FileOrDirectoryDoesNotExistError } from '../errors/path';

export const navigateToDir = (client: Client) => async (path: string) => {
  const pathParts = path
    .toString()
    .split('/')
    .filter((part) => part !== '');

  let currentDirectory = client.metadata.dir;

  for (const pathPart of pathParts) {
    const directory = currentDirectory.children?.find(
      (d: TGFSDirectory) => d.name === pathPart,
    );

    if (!directory) {
      throw new FileOrDirectoryDoesNotExistError(path);
    }

    currentDirectory = directory;
  }

  return currentDirectory;
};
