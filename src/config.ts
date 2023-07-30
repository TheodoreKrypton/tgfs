import fs from 'fs';
import yaml from 'js-yaml';
import path from 'path';

export const config: any = {};

export const loadConfig = (configPath: string) => {
  const file = fs.readFileSync(configPath, 'utf8');
  const cfg = yaml.load(file);

  let TELEGRAM_SESSION_FILE = cfg['telegram']['session_file'];
  if (TELEGRAM_SESSION_FILE[0] === '~') {
    TELEGRAM_SESSION_FILE = path.join(
      process.env.HOME,
      TELEGRAM_SESSION_FILE.slice(1),
    );
  }
  if (!fs.existsSync(TELEGRAM_SESSION_FILE)) {
    const dir = TELEGRAM_SESSION_FILE.substring(
      0,
      TELEGRAM_SESSION_FILE.lastIndexOf('/'),
    );
    fs.mkdirSync(dir, { recursive: true });
  }

  config.TELEGRAM_API_ID = cfg['telegram']['api_id'];
  config.TELEGRAM_API_HASH = cfg['telegram']['api_hash'];
  config.TELEGRAM_SESSION_FILE = TELEGRAM_SESSION_FILE;
  config.TELEGRAM_BOT_TOKEN = cfg['telegram']['bot_token'];
  config.TELEGRAM_PRIVATE_FILE_CHANNEL = `-100${cfg['telegram']['private_file_channel']}`;
  config.TELEGRAM_PUBLIC_FILE_CHANNEL = cfg['telegram']['public_file_channel'];
};
