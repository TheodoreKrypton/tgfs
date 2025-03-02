import fs from 'fs';

import input from 'input';

import { createConfig, loadConfig } from 'src/config';

describe('config', () => {
  const configPath = 'mock-config.yaml';

  afterEach(() => {
    fs.rmSync(configPath);
  });

  it('should guide the user to create a valid config', async () => {
    const answers = {
      'The config file is malformed or not found. Create a config file now?':
        true,
      'Where do you want to save this config file': configPath,
      'Visit https://my.telegram.org/apps, create an app and paste the app_id, app_token here\nApp api_id': 114514,
      'App api_hash': 'mock-api-hash',
      'Where do you want to save the account session': 'here.session',
      'Where do you want to save the bot session': 'there.session',
      'Create a bot from https://t.me/botfather and paste the bot token here\nBot token':
        'mock-bot-token',
      'Create a PRIVATE channel and paste the channel id here\nChannel to store the files':
        '1919810',
      'Do you want to use Azure Key Vault for secrets?': false,
    };

    const getAnswer = async (prompt: string) => {
      return answers[prompt];
    };

    jest.spyOn(input, 'confirm').mockImplementation(getAnswer);
    jest.spyOn(input, 'text').mockImplementation(getAnswer);
    jest.spyOn(fs, 'existsSync').mockImplementation(() => {
      return true;
    });

    await createConfig();
    const config = await loadConfig(configPath);

    expect(config.telegram).toEqual({
      api_id: 114514,
      api_hash: 'mock-api-hash',
      account: { session_file: 'here.session' },
      bot: { token: 'mock-bot-token', session_file: 'there.session' },
      private_file_channel: '-1001919810',
      public_file_channel: '',
    });
    expect(config.tgfs).toEqual({
      users: {
        user: {
          password: 'password',
        },
      },
      download: { chunk_size_kb: 1024 },
    });
    expect(config.webdav).toEqual({ host: '0.0.0.0', port: 1900, path: '/' });

    expect(config.manager.jwt.secret.length).toBe(64);

    config.manager.jwt.secret = 'mock-secret';

    expect(config.manager).toEqual({
      host: '0.0.0.0',
      port: 1901,
      path: '/',
      bot: { token: '', chat_id: 0 },
      jwt: {
        secret: 'mock-secret',
        algorithm: 'HS256',
        life: 3600 * 24 * 7,
      },
    });
  });
});
