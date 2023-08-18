import { TelegramClient } from 'telegram';

import { DirectoryIsNotEmptyError } from '../../errors/path';
import { TGFSDirectory } from '../../model/directory';
import { validateName } from '../../utils/validate-name';
import { MetaDataApi } from './metadata-api';

export class DirectoryApi extends MetaDataApi {
  constructor(protected readonly client: TelegramClient) {
    super(client);
  }

  public async createRootDirectory() {
    await this.resetMetadata();
    await this.syncMetadata();

    return this.metadata.dir;
  }

  public async createDirectoryUnder(name: string, where: TGFSDirectory) {
    validateName(name);

    const newDirectory = where.createChild(name);
    await this.syncMetadata();

    return newDirectory;
  }

  public async deleteEmptyDirectory(directory: TGFSDirectory) {
    if (
      directory.findChildren().length > 0 ||
      directory.findFiles().length > 0
    ) {
      throw new DirectoryIsNotEmptyError();
    }
    await this.deleteDirectory(directory);
  }

  public async deleteDirectory(directory: TGFSDirectory) {
    directory.delete();
    await this.syncMetadata();
  }
}
