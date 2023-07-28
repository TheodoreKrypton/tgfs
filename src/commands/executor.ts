import { Client } from '../api';
import { UnknownCommandError } from '../errors/cmd';
import { cp } from './cp';
import { ls } from './ls';
import { mkdir } from './mkdir';
import { rm } from './rm';
import { touch } from './touch';

export class Executor {
  constructor(private readonly client: Client) {}

  async execute(argv: any) {
    let rsp: any;

    switch (argv._[0]) {
      case 'ls':
        rsp = await ls(this.client)(argv);
        break;
      case 'mkdir':
        rsp = await mkdir(this.client)(argv);
        break;
      case 'cp':
        rsp = await cp(this.client)(argv);
        break;
      case 'rm':
        rsp = await rm(this.client)(argv);
        break;
      case 'touch':
        rsp = await touch(this.client)(argv);
        break;
      default:
        throw new UnknownCommandError(argv._[0]);
    }

    console.log(rsp);
  }
}
