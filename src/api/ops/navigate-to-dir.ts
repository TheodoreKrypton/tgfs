import { Client } from 'src/api';
import { FileOrDirectoryDoesNotExistError } from 'src/errors/path';

export const navigateToDir = (client: Client) => (path: string) => {
  const pathParts = path
    .toString()
    .split('/')
    .filter((part) => part !== '');

  let currentDirectory = client.dir.root();

  for (const pathPart of pathParts) {
    const directory = currentDirectory.findDirs([pathPart])[0];
    if (!directory) {
      throw new FileOrDirectoryDoesNotExistError(path, `navigate to ${path}`);
    }

    currentDirectory = directory;
  }

  return currentDirectory;
};
