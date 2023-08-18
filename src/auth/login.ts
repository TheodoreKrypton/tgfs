import { TelegramClient } from 'telegram';
import { StringSession } from 'telegram/sessions';

import * as fs from 'fs';

import { Client } from 'src/api';
import { config } from 'src/config';
import { Logger } from 'src/utils/logger';

export const login =
  (relogin: (client: TelegramClient) => Promise<void>) =>
  async (reset: boolean = false) => {
    const apiId = config.telegram.api_id;
    const apiHash = config.telegram.api_hash;

    if (!reset && fs.existsSync(config.telegram.session_file)) {
      const session = new StringSession(
        String(fs.readFileSync(config.telegram.session_file)),
      );
      const client = new TelegramClient(session, apiId, apiHash, {
        connectionRetries: 5,
      });

      try {
        await client.connect();
        return new Client(client);
      } catch (err) {
        Logger.error(err);
      }
    }

    const client = new TelegramClient(new StringSession(''), apiId, apiHash, {
      connectionRetries: 5,
    });

    await relogin(client);

    fs.writeFileSync(
      config.telegram.session_file,
      String(client.session.save()),
    );

    return new Client(client);
  };
