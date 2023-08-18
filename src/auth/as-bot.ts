import { config } from 'src/config';
import { Logger } from 'src/utils/logger';

import { login } from './login';

export const loginAsBot = login(async (client) => {
  await client.start({
    botAuthToken: config.telegram.bot_token,
    onError: (err) => Logger.error(err),
  });
});
