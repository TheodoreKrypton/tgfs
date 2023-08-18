#!/usr/bin/env node
import fs from 'fs';
import { exit } from 'process';
import yargs from 'yargs';
import { hideBin } from 'yargs/helpers';

import { Client } from './api';
import { loginAsUser } from './auth';
import { Executor } from './commands/executor';
import { parser } from './commands/parser';
import { config, createConfig, loadConfig } from './config';
import { BusinessError } from './errors/base';
import { runWebDAVServer } from './server/webdav';
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
  loadConfig(configPath);

  let client: Client;
  const res = await Promise.race([loginAsUser(), sleep(300000)]);
  if (res instanceof Client) {
    client = res;
  } else {
    Logger.error('login timeout');
    exit(1);
  }

  await client.init();

  // runSync();

  if (argv.webdav) {
    await runWebDAVServer(client, {
      port: argv.port ?? config.webdav.port,
      hostname: argv.host ?? config.webdav.host,
    });
  } else if (argv._[0] === 'cmd') {
    argv._.shift();
    try {
      const executor = new Executor(client);
      await executor.execute(argv);
      exit(0);
    } catch (err) {
      if (err instanceof BusinessError) {
        Logger.error(err);
      } else {
        console.error(`err\n${err.stack}`);
      }
    }
  }
})();
