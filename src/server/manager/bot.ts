import { Telegraf } from 'telegraf';
import { message } from 'telegraf/filters';

import { config } from 'src/config';
import { Logger } from 'src/utils/logger';

export const createBot = () => {
  const bot = new Telegraf(config.manager.bot.token);

  bot.use(async (ctx, next) => {
    if (ctx.chat.id !== config.manager.bot.chat_id) {
      return;
    }
    await next();
  });

  bot.catch((err) => {
    console.error(err);
  });

  bot.on(message('sticker'), (ctx) => ctx.reply('👍'));
  bot.hears('hi', (ctx) => ctx.reply(ctx.chat.id.toString()));
  return bot;
};

export const startBot = () => {
  const bot = createBot();

  bot.launch().catch((err) => {
    if (err.code === 'ETIMEOUT') {
      Logger.error('Timeout when connecting to Telegram Bot API, retrying...');
      // retry until success
      setTimeout(() => {
        startBot();
      }, 100);
    }
  });
};
