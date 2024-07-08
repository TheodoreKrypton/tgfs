import { Client } from 'src/api';
import { FileOrDirectoryDoesNotExistError } from 'src/errors/path';
import { TGFSDirectory } from 'src/model/directory';

import { navigateToDir } from './navigate-to-dir';
import { splitPath } from './utils';

export const copyDir =
  (client: Client) =>
  async (
    pathFrom: string,
    pathTo: string,
  ): Promise<{
    from: TGFSDirectory;
    to: TGFSDirectory;
  }> => {
    const [basePathFrom, nameFrom] = splitPath(pathFrom);
    if (nameFrom === '') {
      return;
    }

    const dir = navigateToDir(client)(basePathFrom);
    const dirToCopy = dir.findDirs([nameFrom])[0];

    if (!dirToCopy) {
      throw new FileOrDirectoryDoesNotExistError(
        pathFrom,
        `move directory from ${pathFrom} to ${pathTo}`,
      );
    }

    const [basePathTo, nameTo] = splitPath(pathTo);
    const dir2 = navigateToDir(client)(basePathTo);

    const res = await client.createDirectory(
      { name: nameTo ?? nameFrom, under: dir2 },
      dirToCopy,
    );

    return { from: dirToCopy, to: res };
  };
