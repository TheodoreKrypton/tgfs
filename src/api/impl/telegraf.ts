import { Telegram } from 'telegraf';

import { IBot } from 'src/api/interface';
import { Config } from 'src/config';

export const createBot = (config: Config): Telegram => {
  return new Telegram(config.telegram.bot.token);
};

export class TelegrafApi implements IBot {
  constructor(protected readonly bot: Telegram) {}
}
