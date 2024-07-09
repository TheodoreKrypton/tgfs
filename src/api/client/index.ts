import { gramjs, telegraf } from 'src/api/impl';
import { config } from 'src/config';

import { DirectoryApi } from './directory-api';
import { FileDescApi } from './file-desc-api';
import { FileRefApi } from './file-ref-api';
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

  const frApi = new FileRefApi(metadataApi, fdApi);
  const dirApi = new DirectoryApi(metadataApi);

  return new Client(metadataApi, frApi, dirApi);
};

export class Client {
  file: FileRefApi;
  dir: DirectoryApi;

  constructor(
    private readonly metadataApi: MetaDataApi,
    private readonly frApi: FileRefApi,
    private readonly dirApi: DirectoryApi,
  ) {
    this.file = this.frApi;
    this.dir = this.dirApi;
  }
}
