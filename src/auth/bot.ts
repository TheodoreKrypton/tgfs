import { Telegram } from 'telegraf';

import { config } from 'src/config';

export const loginAsBot = (): Telegram => {
  return new Telegram(config.telegram.bot.token);
};
