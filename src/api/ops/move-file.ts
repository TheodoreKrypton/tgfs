import { Client } from 'src/api';
import { FileOrDirectoryDoesNotExistError } from 'src/errors/path';

import { navigateToDir } from './navigate-to-dir';
import { splitPath } from './utils';

export const moveFile =
  (client: Client) => async (pathFrom: string, pathTo: string) => {
    const [dirFrom, nameFrom] = splitPath(pathFrom);
    const dir = navigateToDir(client)(dirFrom);
    const fileRef = dir.findFiles([nameFrom])[0];

    if (!fileRef) {
      throw new FileOrDirectoryDoesNotExistError(
        pathFrom,
        `move file from ${pathFrom} to ${pathTo}`,
      );
    }

    const [dirTo, nameTo] = splitPath(pathTo);

    try {
      const dir2 = navigateToDir(client)(dirTo);
      dir2.createFileRef(nameTo, fileRef.getMessageId());
      await client.deleteFile(fileRef);
    } catch (err) {
      throw new FileOrDirectoryDoesNotExistError(
        dirTo,
        `move file from ${pathFrom} to ${pathTo}`,
      );
    }
  };
