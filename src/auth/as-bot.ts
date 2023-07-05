import { config } from '../config';
import { Logger } from '../utils/logger';
import { login } from './login';

export const loginAsBot = login(async (client) => {
  await client.start({
    botAuthToken: config.TELEGRAM_BOT_TOKEN,
    onError: (err) => Logger.error(err),
  });
});
