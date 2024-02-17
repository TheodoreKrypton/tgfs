import fs from 'fs';

import input from 'input';
import yaml from 'js-yaml';
import os from 'os';
import path from 'path';

export type Config = {
  telegram: {
    api_id: number;
    api_hash: string;
    account: {
      session_file: string;
    };
    bot: {
      token: string;
      session_file: string;
    };
    private_file_channel: string;
    public_file_channel: string;
  };
  tgfs: {
    users: {
      [key: string]: {
        password: string;
      };
    };
    download: {
      chunk_size_kb: number;
    };
  };
  webdav: {
    host: string;
    port: number;
    path: string;
  };
  manager: {
    host: string;
    port: number;
    path: string;
    bot: {
      token: string;
      chat_id: number;
    };
    jwt: {
      secret: string;
      algorithm: string;
      expiration: number;
    };
  };
};

export let config: Config;

export const loadConfig = (configPath: string): Config => {
  const file = fs.readFileSync(configPath, 'utf8');
  const cfg = yaml.load(file);

  const getSessionFilePath = (session_file: string) => {
    if (session_file[0] === '~') {
      session_file = path.join(os.homedir(), session_file.slice(1));
    }
    if (!fs.existsSync(session_file)) {
      const dir = path.dirname(session_file);
      fs.mkdirSync(dir, { recursive: true });
    }

    return session_file;
  };

  config = {
    telegram: {
      api_id: cfg['telegram']['api_id'],
      api_hash: cfg['telegram']['api_hash'],
      account: {
        session_file: getSessionFilePath(
          cfg['telegram']['account']['session_file'],
        ),
      },
      bot: {
        token: cfg['telegram']['bot']['token'],
        session_file: getSessionFilePath(
          cfg['telegram']['bot']['session_file'],
        ),
      },
      private_file_channel: `-100${cfg['telegram']['private_file_channel']}`,
      public_file_channel: cfg['telegram']['public_file_channel'],
    },
    tgfs: {
      users: cfg['tgfs']['users'],
      download: {
        chunk_size_kb: cfg['tgfs']['download']['chunk_size_kb'] ?? 1024,
      },
    },
    webdav: {
      host: cfg['webdav']['host'] ?? '0.0.0.0',
      port: cfg['webdav']['port'] ?? 1900,
      path: cfg['webdav']['path'] ?? '/',
    },
    manager: {
      host: cfg['manager']['host'] ?? '0.0.0.0',
      port: cfg['manager']['port'] ?? 1901,
      path: cfg['manager']['path'] ?? '/',
      bot: {
        token: cfg['manager']['bot']['token'],
        chat_id: cfg['manager']['bot']['chat_id'],
      },
      jwt: {
        secret: cfg['manager']['jwt']['secret'],
        algorithm: cfg['manager']['jwt']['algorithm'] ?? 'HS256',
        expiration: cfg['manager']['jwt']['expiration'],
      },
    },
  };
  return config;
};

export const createConfig = async (): Promise<string> => {
  const createNow = await input.confirm(
    'The config file is malformed or not found. Create a config file now?',
  );

  if (!createNow) {
    process.exit(0);
  }

  const validateNotEmpty = (answer: string) => {
    if (answer.trim().length > 0) {
      return true;
    } else {
      return 'This field is mandatory!';
    }
  };

  const configPath = await input.text(
    'Where do you want to save this config file',
    { default: path.join(process.cwd(), 'config.yaml') },
  );

  const generateRandomSecret = () => {
    const chars =
      'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    let secret = '';
    for (let i = 0; i < 64; i++) {
      secret += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return secret;
  };

  const res: Config = {
    telegram: {
      api_id: Number(
        await input.text(
          'Visit https://my.telegram.org/apps, create an app and paste the app_id, app_token here\nApp api_id',
          {
            validate: validateNotEmpty,
          },
        ),
      ),
      api_hash: (await input.text('App api_hash', {
        validate: validateNotEmpty,
      })) as string,
      account: {
        session_file: (await input.text(
          'Where do you want to save the account session',
          { default: '~/.tgfs/account.session' },
        )) as string,
      },
      bot: {
        session_file: (await input.text(
          'Where do you want to save the bot session',
          { default: '~/.tgfs/bot.session' },
        )) as string,
        token: (await input.text(
          'Create a bot from https://t.me/botfather and paste the bot token here\nBot token',
          {
            validate: validateNotEmpty,
          },
        )) as string,
      },
      private_file_channel: await input.text(
        'Create a PRIVATE channel and paste the channel id here\nChannel to store the files',
        {
          validate: validateNotEmpty,
        },
      ),
      public_file_channel: '',
    },
    tgfs: {
      users: {
        user: {
          password: 'password',
        },
      },
      download: {
        chunk_size_kb: 1024,
      },
    },
    webdav: {
      host: '0.0.0.0',
      port: 1900,
      path: '/',
    },
    manager: {
      host: '0.0.0.0',
      port: 1901,
      path: '/',
      bot: {
        token: '',
        chat_id: 0,
      },
      jwt: {
        secret: generateRandomSecret(),
        algorithm: 'HS256',
        expiration: 3600 * 24 * 7,
      },
    },
  };

  const yamlString = yaml.dump(res);

  fs.writeFileSync(configPath, yamlString);
  return configPath;
};
