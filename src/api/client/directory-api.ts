import { TelegramClient } from 'telegram';

import { DirectoryIsNotEmptyError } from '../../errors/path';
import { TGFSDirectory } from '../../model/directory';
import { validateName } from '../../utils/validate-name';
import { MetaDataApi } from './metadata-api';

export class DirectoryApi extends MetaDataApi {
  constructor(protected readonly client: TelegramClient) {
    super(client);
  }

  protected async createRootDirectory() {
    await this.resetMetadata();
    await this.syncMetadata();

    return this.getRootDirectory();
  }

  public async createDirectory(where: { name: string; under: TGFSDirectory }) {
    validateName(where.name);

    const newDirectory = where.under.createChild(where.name);
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
    await this.dangerouslyDeleteDirectory(directory);
  }

  public async dangerouslyDeleteDirectory(directory: TGFSDirectory) {
    directory.delete();
    await this.syncMetadata();
  }
}
