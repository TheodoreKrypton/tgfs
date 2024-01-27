import * as fs from 'fs';

import { TelegramClient } from 'telegram';
import { StringSession } from 'telegram/sessions';

import * as input from 'input';

import { config } from 'src/config';
import { Logger } from 'src/utils/logger';

export const loginAsAccount = async (
  reset: boolean = false,
): Promise<TelegramClient> => {
  const apiId = config.telegram.account.api_id;
  const apiHash = config.telegram.account.api_hash;
  const session_file = config.telegram.account.session_file;

  if (!reset && fs.existsSync(session_file)) {
    console.log(`using session file: ${session_file}`);
    const session = new StringSession(String(fs.readFileSync(session_file)));
    const client = new TelegramClient(session, apiId, apiHash, {
      connectionRetries: 5,
    });

    try {
      await client.connect();
      return client;
    } catch (err) {
      Logger.error(err);
    }
  }

  const client = new TelegramClient(new StringSession(''), apiId, apiHash, {
    connectionRetries: 5,
  });

  await client.start({
    phoneNumber: async () => await input.text('phone number?'),
    password: async () => await input.text('password?'),
    phoneCode: async () => await input.text('one-time code?'),
    onError: (err) => Logger.error(err),
  });

  fs.writeFileSync(config.telegram.session_file, String(client.session.save()));

  return client;
};
