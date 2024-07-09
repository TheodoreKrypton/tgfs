import { gramjs, telegraf } from 'src/api/impl';
import { config } from 'src/config';

import { DirectoryApi } from './directory-api';
import { FileApi } from './file-api';
import { FileDescApi } from './file-desc-api';
import { MessageApi } from './message-api';
import { MetaDataApi } from './metadata-api';
import { TGMsgFDRepository } from './repository/impl/fd/tg-msg';
import { FileRepository } from './repository/impl/file';
import { JSONMetadataRepository } from './repository/impl/metadata/tg-msg';

export const createClient = async () => {
  const msgApi = new MessageApi(
    {
      account: new gramjs.GramJSApi(await gramjs.loginAsAccount(config)),
      bot: new gramjs.GramJSApi(await gramjs.loginAsBot(config)),
    },
    new telegraf.TelegrafApi(telegraf.createBot(config)),
  );

  const fileRepo = new FileRepository(msgApi);
  const fdRepo = new TGMsgFDRepository(msgApi);
  const metadataRepo = new JSONMetadataRepository(msgApi, fileRepo);

  const fdApi = new FileDescApi(fdRepo, fileRepo);

  const metadataApi = new MetaDataApi(metadataRepo);
  await metadataApi.init();

  const fileApi = new FileApi(metadataApi, fdApi);
  const dirApi = new DirectoryApi(metadataApi);

  return new Client(fileApi, dirApi);
};

export class Client {
  file: FileApi;
  dir: DirectoryApi;

  constructor(
    private readonly fileApi: FileApi,
    private readonly dirApi: DirectoryApi,
  ) {
    this.file = this.fileApi;
    this.dir = this.dirApi;
  }
}
