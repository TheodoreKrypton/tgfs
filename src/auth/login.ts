import * as fs from 'fs';
import { TelegramClient } from 'telegram';
import { StringSession } from 'telegram/sessions';

import { Client } from '../api';
import { config } from '../config';
import { Logger } from '../utils/logger';

const apiId = config.TELEGRAM_API_ID;
const apiHash = config.TELEGRAM_API_HASH;

export const login =
  (relogin: (client: TelegramClient) => Promise<void>) =>
  async (reset: boolean = false) => {
    if (!reset && fs.existsSync(config.TELEGRAM_SESSION_FILE)) {
      const session = new StringSession(
        String(fs.readFileSync(config.TELEGRAM_SESSION_FILE)),
      );
      const client = new TelegramClient(session, apiId, apiHash, {
        connectionRetries: 5,
      });

      try {
        await client.connect();
        return new Client(client, config.TELEGRAM_PRIVATE_FILE_CHANNEL);
      } catch (err) {
        Logger.error(err);
      }
    }

    const client = new TelegramClient(new StringSession(''), apiId, apiHash, {
      connectionRetries: 5,
    });

    await relogin(client);

    fs.writeFileSync(
      config.TELEGRAM_SESSION_FILE,
      String(client.session.save()),
    );

    return new Client(client, config.TELEGRAM_PRIVATE_FILE_CHANNEL);
  };
