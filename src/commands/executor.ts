import { Client } from '../api';
import { cp } from './cp';
import { ls } from './ls';
import { mkdir } from './mkdir';
import { rm } from './rm';

export class Executor {
  constructor(private readonly client: Client) {}

  async execute(argv: any) {
    let rsp: any;

    switch (argv._[0]) {
      case 'ls':
        rsp = await ls(this.client)(argv.path);
        break;
      case 'mkdir':
        rsp = await mkdir(this.client)(argv.path);
        break;
      case 'cp':
        rsp = await cp(this.client)(argv.local, argv.remote);
        break;
      case 'rm':
        rsp = await rm(this.client)(argv.path, argv.recursive);
        break;
      default:
        throw new Error('Unknown command');
    }

    console.log(rsp);
  }
}
