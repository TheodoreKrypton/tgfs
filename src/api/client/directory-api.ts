import {
  DirectoryIsNotEmptyError,
  FileOrDirectoryDoesNotExistError,
} from 'src/errors/path';
import { TGFSDirectory, TGFSFileRef } from 'src/model/directory';
import { validateName } from 'src/utils/validate-name';

import { MetaDataApi } from './metadata-api';

export class DirectoryApi {
  constructor(private metadataApi: MetaDataApi) {}



  public async createDirectory(
    where: { name: string; under: TGFSDirectory },
    dir?: TGFSDirectory,
  ) {
    validateName(where.name);

    const newDirectory = where.under.createDir(where.name, dir);
    await this.metadataApi.syncMetadata();

    return newDirectory;
  }

  public ls(
    dir: TGFSDirectory,
    fileName?: string,
  ): TGFSFileRef | Array<TGFSDirectory | TGFSFileRef> {
    if (fileName) {
      const file = dir.findFile(fileName);
      if (file) {
        return file;
      }
      throw new FileOrDirectoryDoesNotExistError(fileName, 'list');
    }
    return [...dir.findDirs(), ...dir.findFiles()];
  }

  public async deleteEmptyDirectory(directory: TGFSDirectory) {
    if (directory.findDirs().length > 0 || directory.findFiles().length > 0) {
      throw new DirectoryIsNotEmptyError();
    }
    await this.dangerouslyDeleteDirectory(directory);
  }

  public async dangerouslyDeleteDirectory(directory: TGFSDirectory) {
    directory.delete();
    await this.metadataApi.syncMetadata();
  }
}
