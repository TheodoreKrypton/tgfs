import { hideBin } from 'yargs/helpers';
import yargs from 'yargs/yargs';

import { loginAsBot } from './auth';
import { Executor } from './commands/executor';

const parse = () => {
  const argv: any = yargs(hideBin(process.argv))
    .command('ls <path>', 'list all files and directories', {
      path: {
        type: 'string',
        description: 'path to list',
      },
    })
    .command('mkdir <path>', 'create a directory', {
      path: {
        type: 'string',
        description: 'path to create',
      },
    })
    .demandCommand(1, 'You need at least one command before moving on')
    .help().argv;

  return argv;
};

(async () => {
  try {
    const client = await loginAsBot();

    await client.init();

    const executor = new Executor(client);

    const argv = parse();
    await executor.execute(argv);
  } catch (err) {
    console.log(err.message);
  } finally {
    process.exit(0);
  }
})();
