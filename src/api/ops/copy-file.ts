import { Client } from 'src/api';
import { FileOrDirectoryDoesNotExistError } from 'src/errors/path';
import { TGFSFileRef } from 'src/model/directory';

import { navigateToDir } from './navigate-to-dir';
import { splitPath } from './utils';

export const copyFile =
  (client: Client) =>
  async (
    pathFrom: string,
    pathTo: string,
  ): Promise<{
    from: TGFSFileRef;
    to: TGFSFileRef;
  }> => {
    const [basePathFrom, nameFrom] = splitPath(pathFrom);
    const dir = navigateToDir(client)(basePathFrom);
    const frToCopy = dir.findFiles([nameFrom])[0];

    if (!frToCopy) {
      throw new FileOrDirectoryDoesNotExistError(
        pathFrom,
        `move file from ${pathFrom} to ${pathTo}`,
      );
    }

    const [basePathTo, nameTo] = splitPath(pathTo);
    const dir2 = navigateToDir(client)(basePathTo);

    const res = await client.file.copy(dir2, frToCopy, nameTo ?? nameFrom);
    return { from: frToCopy, to: res };
  };
