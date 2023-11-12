import fs from 'fs';
import input from 'input';
import yaml from 'js-yaml';
import os from 'os';
import path from 'path';

export const config: any = {};

export const loadConfig = (configPath: string) => {
  const file = fs.readFileSync(configPath, 'utf8');
  const cfg = yaml.load(file);

  let session_file = cfg['telegram']['session_file'];
  if (session_file[0] === '~') {
    session_file = path.join(os.homedir(), session_file.slice(1));
  }
  if (!fs.existsSync(session_file)) {
    const dir = path.dirname(session_file);
    fs.mkdirSync(dir, { recursive: true });
  }

  config.telegram = {
    api_id: cfg['telegram']['api_id'],
    api_hash: cfg['telegram']['api_hash'],
    bot_token: cfg['telegram']['bot_token'],
    private_file_channel: `-100${cfg['telegram']['private_file_channel']}`,
    public_file_channel: cfg['telegram']['public_file_channel'],
    session_file: session_file,
  };

  config.tgfs = {
    users: cfg['tgfs']['users'],
    download: {
      chunksize: cfg['tgfs']['download']['chunk_size_kb'] ?? 1024,
      progress: cfg['tgfs']['download']['progress'] === 'true',
    },
  };

  config.webdav = {
    host: cfg['webdav']['host'] ?? '0.0.0.0',
    port: cfg['webdav']['port'] ?? 1900,
    path: cfg['webdav']['path'] ?? '/',
  };

  config.monitor = {
  };
};

export const createConfig = async () => {
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

  const config: any = {};

  const configPath = await input.text(
    'Where do you want to save the config file',
    { default: path.join(process.cwd(), 'config.yaml') },
  );

  config.telegram = {};

  console.log(
    '\nGo to https://my.telegram.org/apps, follow the steps to log in and paste the App api_id and App api_hash here',
  );
  config.telegram.api_id = Number(
    await input.text('App api_id', { validate: validateNotEmpty }),
  );
  config.telegram.api_hash = await input.text('App api_hash', {
    validate: validateNotEmpty,
  });
  config.telegram.session_file = await input.text(
    'Where do you want to save the session',
    { default: '~/.tgfs/account.session' },
  );

  console.log('\nCreate a PRIVATE channel and paste the channel id here');
  config.telegram.private_file_channel = Number(
    await input.text('Channel to store the files', {
      validate: validateNotEmpty,
    }),
  );

  config.tgfs = {
    host: '0.0.0.0',
    port: 1900,
    users: {
      user: {
        password: 'password',
      },
    },
    download: {
      progress: 'true',
      chunk_size_kb: 1024,
    },
  };

  config.webdav = {
    path: '/webdav',
  };

  config.monitor = {
    path: '/monitor',
  };

  const yamlString = yaml.dump(config);

  fs.writeFileSync(configPath, yamlString);
  return configPath;
};
