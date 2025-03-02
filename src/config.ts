import fs from 'fs';

import input from 'input';
import yaml from 'js-yaml';
import os from 'os';
import path from 'path';
import { KeyVaultClient, getSecretOrDefault } from './utils/key-vault';
import { Logger } from './utils/logger';

export type Config = {
  azure?: {
    key_vault?: {
      url: string;
      enabled: boolean;
      secret_mapping?: {
        api_id?: string;
        api_hash?: string;
        bot_token?: string;
        private_file_channel?: string;
        password?: string;
        jwt_secret?: string;
      };
    };
  };
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
      life: number;
    };
  };
};

export let config: Config;

export const loadConfig = async (configPath: string): Promise<Config> => {
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

  // Initialize Key Vault client if enabled
  let keyVaultClient: KeyVaultClient | null = null;
  const azureConfig = cfg['azure']?.['key_vault'];
  const useKeyVault = azureConfig?.enabled === true && azureConfig?.url;
  
  if (useKeyVault) {
    Logger.info('Azure Key Vault integration enabled, initializing client...');
    keyVaultClient = KeyVaultClient.getInstance(azureConfig.url);
    if (!keyVaultClient.isInitialized()) {
      Logger.warn('Failed to initialize Azure Key Vault client, falling back to file-based configuration');
    }
  }

  // Load secrets from Key Vault or config file
  const secretMapping = azureConfig?.secret_mapping || {};
  
  // Load API ID (convert to number)
  const apiIdSecret = useKeyVault && secretMapping.api_id 
    ? await getSecretOrDefault(keyVaultClient, secretMapping.api_id, cfg['telegram']['api_id'])
    : cfg['telegram']['api_id'];
  
  // Load API Hash
  const apiHashSecret = useKeyVault && secretMapping.api_hash
    ? await getSecretOrDefault(keyVaultClient, secretMapping.api_hash, cfg['telegram']['api_hash'])
    : cfg['telegram']['api_hash'];
  
  // Load Bot Token
  const botTokenSecret = useKeyVault && secretMapping.bot_token
    ? await getSecretOrDefault(keyVaultClient, secretMapping.bot_token, cfg['telegram']['bot']['token'])
    : cfg['telegram']['bot']['token'];
  
  // Load Private File Channel
  const privateFileChannelSecret = useKeyVault && secretMapping.private_file_channel
    ? await getSecretOrDefault(keyVaultClient, secretMapping.private_file_channel, cfg['telegram']['private_file_channel'])
    : cfg['telegram']['private_file_channel'];
  
  // Load JWT Secret
  const jwtSecretSecret = useKeyVault && secretMapping.jwt_secret
    ? await getSecretOrDefault(keyVaultClient, secretMapping.jwt_secret, cfg['manager']['jwt']['secret'])
    : cfg['manager']['jwt']['secret'];

  // Load user passwords
  const users = cfg['tgfs']['users'] || {};
  if (useKeyVault && secretMapping.password) {
    for (const username in users) {
      const passwordKey = `${secretMapping.password}-${username}`;
      users[username].password = await getSecretOrDefault(
        keyVaultClient, 
        passwordKey, 
        users[username].password
      );
    }
  }

  config = {
    azure: cfg['azure'],
    telegram: {
      api_id: Number(apiIdSecret),
      api_hash: apiHashSecret,
      account: {
        session_file: getSessionFilePath(
          cfg['telegram']['account']['session_file'],
        ),
      },
      bot: {
        token: botTokenSecret,
        session_file: getSessionFilePath(
          cfg['telegram']['bot']['session_file'],
        ),
      },
      private_file_channel: `-100${privateFileChannelSecret}`,
      public_file_channel: cfg['telegram']['public_file_channel'],
    },
    tgfs: {
      users: users,
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
        secret: jwtSecretSecret,
        algorithm: cfg['manager']['jwt']['algorithm'] ?? 'HS256',
        life: cfg['manager']['jwt']['life'],
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

  const useAzureKeyVault = await input.confirm(
    'Do you want to use Azure Key Vault for secrets?',
    { default: false }
  );

  let azureConfig = undefined;
  if (useAzureKeyVault) {
    const keyVaultUrl = await input.text(
      'Enter your Azure Key Vault URL (e.g., https://your-vault.vault.azure.net/)',
      { validate: validateNotEmpty }
    );

    azureConfig = {
      key_vault: {
        url: keyVaultUrl,
        enabled: true,
        secret_mapping: {
          api_id: await input.text('Secret name for api_id in Key Vault', { default: 'tgfs-api-id' }),
          api_hash: await input.text('Secret name for api_hash in Key Vault', { default: 'tgfs-api-hash' }),
          bot_token: await input.text('Secret name for bot token in Key Vault', { default: 'tgfs-bot-token' }),
          private_file_channel: await input.text('Secret name for private_file_channel in Key Vault', { default: 'tgfs-private-file-channel' }),
          password: await input.text('Base secret name for user passwords in Key Vault (will be suffixed with username)', { default: 'tgfs-user-password' }),
          jwt_secret: await input.text('Secret name for JWT secret in Key Vault', { default: 'tgfs-jwt-secret' }),
        }
      }
    };
  }

  const res: Config = {
    azure: azureConfig,
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
        life: 3600 * 24 * 7,
      },
    },
  };

  const yamlString = yaml.dump(res);

  fs.writeFileSync(configPath, yamlString);
  return configPath;
};
