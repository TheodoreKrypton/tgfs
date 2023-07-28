import { hideBin } from 'yargs/helpers';
import yargs from 'yargs/yargs';

export const parse = () => {
  const argv: any = yargs(hideBin(process.argv))
    .command('ls <path>', 'list all files and directories', {
      path: {
        type: 'string',
        description: 'path to list',
      },
    })
    .command('mkdir <path>', 'create a directory', (yargs) => {
      return yargs
        .positional('path', {
          type: 'string',
          description: 'path to create',
        })
        .option('p', {
          alias: 'parents',
          type: 'boolean',
          description:
            'no error if existing, make parent directories as needed',
        });
    })
    .command('cp <local> <remote>', 'upload a file', {
      local: {
        type: 'string',
      },
      remote: {
        type: 'string',
      },
    })
    .command('rm <path>', 'remove a file or directory', (yargs) => {
      return yargs
        .positional('path', {
          describe: 'File or directory to remove',
          type: 'string',
        })
        .option('r', {
          alias: 'recursive',
          describe: 'remove a directory and its contents recursively',
          type: 'boolean',
        });
    })
    .command('touch <path>', 'create a file', (yargs) => {
      return yargs.positional('path', {
        describe: 'path to create',
        type: 'string',
      });
    })
    .demandCommand(1, 'You need at least one command before moving on')
    .help().argv;

  return argv;
};
