import { gramjs, telegraf } from 'src/api/impl';
import { config } from 'src/config';

import { FileApi } from './file-api';

export const createClient = async () => {
  const client = new Client(
    new gramjs.GramJSApi(
      await gramjs.loginAsAccount(config),
      await gramjs.loginAsBot(config),
    ),
    new telegraf.TelegrafApi(telegraf.createBot(config)),
  );
  await client.init();
  return client;
};

export class Client extends FileApi {
  public async init() {
    await this.initMetadata();
    if (!this.getRootDirectory()) {
      await this.createRootDirectory();
    }
  }
}
