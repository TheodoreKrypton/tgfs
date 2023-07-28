import { Client } from '..';
import { FileOrDirectoryDoesNotExistError } from '../../errors/path';

export const navigateToDir = (client: Client) => async (path: string) => {
  const pathParts = path
    .toString()
    .split('/')
    .filter((part) => part !== '');

  let currentDirectory = client.getRootDirectory();

  for (const pathPart of pathParts) {
    const directory = currentDirectory.findChildren([pathPart])[0];
    if (!directory) {
      throw new FileOrDirectoryDoesNotExistError(path);
    }

    currentDirectory = directory;
  }

  return currentDirectory;
};
