#!/usr/bin/env node
import express from 'express';
import fs from 'fs';

import { TelegramClient } from 'telegram';

import { Telegraf } from 'telegraf';

import ip from 'ip';
import { exit } from 'process';
import { v2 as webdav } from 'webdav-server';
import yargs from 'yargs';
import { hideBin } from 'yargs/helpers';

import { Client } from './api';
import { loginAsAccount, loginAsBot } from './auth';
import { Executor } from './commands/executor';
import { parser } from './commands/parser';
import { config, createConfig, loadConfig } from './config';
import { BusinessError } from './errors/base';
import { managerServer, startBot } from './server/manager';
import { webdavServer } from './server/webdav';
import { Logger } from './utils/logger';
import { sleep } from './utils/sleep';

const { argv }: any = yargs(hideBin(process.argv))
  .option('config', {
    alias: 'f',
    describe: 'config file path',
    type: 'string',
    default: './config.yaml',
  })
  .option('webdav', {
    alias: 'w',
    describe: 'start webdav server',
    type: 'boolean',
    default: false,
  })
  .command('cmd *', 'run command', parser);

(async () => {
  let configPath = argv.config;
  if (!fs.existsSync(configPath)) {
    configPath = await createConfig();
  }

  try {
    loadConfig(configPath);
  } catch (err) {
    configPath = await createConfig();
    loadConfig(configPath);
  }

  // account login
  let account: TelegramClient;
  let res = await Promise.race([loginAsAccount(), sleep(300000)]);
  if (res instanceof TelegramClient) {
    account = res;
  } else {
    Logger.error('account login timeout');
    exit(1);
  }

  // bot login
  let bot = loginAsBot();

  const client = new Client(account, bot);
  await client.init();

  // runSync();

  const startServer = (
    name: string,
    app: (req: any, res: any, next: any) => void,
    host: string,
    port: number,
    path: string,
  ) => {
    const masterApp = express();
    masterApp.use(path, app);
    masterApp.listen(port, host);

    if (host === '0.0.0.0' || host === '::') {
      host = ip.address();
    }
    Logger.info(`${name} is running on ${host}:${port}${path}`);
  };

  if (argv.webdav) {
    const server = webdavServer(client);
    startServer(
      'WebDAV',
      webdav.extensions.express('/', server),
      config.webdav.host,
      config.webdav.port,
      config.webdav.path,
    );
  } else if (argv._[0] === 'cmd') {
    argv._.shift();
    try {
      const executor = new Executor(client);
      await executor.execute(argv);
    } catch (err) {
      if (err instanceof BusinessError) {
        Logger.error(err);
      } else {
        console.error(`err\n${err.stack}`);
      }
    } finally {
      exit(0);
    }
  }

  startServer(
    'Manager',
    (req, res, next) => {
      managerServer(req, res);
      next();
    },
    config.manager.host,
    config.manager.port,
    config.manager.path,
  );

  startBot();
})();
