import fs from 'fs';
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
    login: cfg['telegram']['login'],
  };

  config.tgfs = {
    download: {
      chunksize: cfg['tgfs']['download']['chunk_size_kb'] ?? 1024,
      progress: cfg['tgfs']['download']['progress'] ?? true,
    },
  };

  config.webdav = {
    host: cfg['webdav']['host'],
    port: cfg['webdav']['port'],
    users: cfg['webdav']['users'],
  };

  config.sync = cfg['sync'];
};
