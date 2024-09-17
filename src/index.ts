#!/usr/bin/env node
import express from 'express';
import fs from 'fs';



import { exit } from 'process';
import { v2 as webdav } from 'webdav-server';
import yargs from 'yargs';
import { hideBin } from 'yargs/helpers';

import { createClient } from './api';
import { Executor } from './commands/executor';
import { parser } from './commands/parser';
import { config, createConfig, loadConfig } from './config';
import { BusinessError } from './errors/base';
import { managerServer, startBot } from './server/manager';
import { webdavServer } from './server/webdav';
import { getIPAddress } from './utils/ip-address';
import { Logger } from './utils/logger';

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
    Logger.debug(err);
    configPath = await createConfig();
    loadConfig(configPath);
  }

  const client = await createClient();

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

    let addresses = [`://${host}:${port}${path}`];

    if (host === '0.0.0.0' || host === '::') {
      addresses = getIPAddress('IPv4').map((ip) => `://${ip}:${port}${path}`);
    }
    Logger.info(`${name} is running on ${addresses.join(', ')}`);
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

  managerServer.listen(config.manager.port, config.manager.host);

  // startServer(
  //   'Manager',
  //   (req, res, next) => {
  //     managerServer(req, res);
  //     next();
  //   },
  //   config.manager.host,
  //   config.manager.port,
  //   config.manager.path,
  // );

  startBot();
})();