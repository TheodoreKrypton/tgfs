import dotenv from 'dotenv';
import * as fs from 'fs';
import * as path from 'path';

const env = dotenv.config({
  path: `.env.${process.env.NODE_ENV ?? 'local'}`,
}).parsed;

let TELEGRAM_SESSION_FILE = env.TELEGRAM_SESSION_FILE;
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

export const config = {
  TELEGRAM_API_ID: parseInt(env.TELEGRAM_API_ID),
  TELEGRAM_API_HASH: env.TELEGRAM_API_HASH,
  TELEGRAM_SESSION: env.TELEGRAM_SESSION,
  TELEGRAM_SESSION_FILE: TELEGRAM_SESSION_FILE,
  TELEGRAM_BOT_TOKEN: env.TELEGRAM_BOT_TOKEN,
  TELEGRAM_PRIVATE_FILE_CHANNEL: `-100${env.TELEGRAM_PRIVATE_FILE_CHANNEL}`,
  TELEGRAM_PUBLIC_FILE_CHANNEL: env.TELEGRAM_PUBLIC_FILE_CHANNEL,
};
