import { hideBin } from 'yargs/helpers';
import yargs from 'yargs/yargs';

import { ls } from './ls';

const argv: any = yargs(hideBin(process.argv))
  .command('ls', 'list all files', (yargs) => {
    return yargs.option('path', {
      describe: 'Path to list files from',
      demandOption: true,
      type: 'string',
    });
  })
  .demandCommand(1, 'You need at least one command before moving on')
  .help().argv;

if (argv._[0] === 'ls') {
  ls(argv.path);
} else if (argv._[0] === 'get') {
} else if (argv._[0] === 'send') {
}
