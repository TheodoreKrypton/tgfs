import { Client } from '../api';
import { ls } from './ls';
import { mkdir } from './mkdir';

export class Executor {
  constructor(private readonly client: Client) {}

  async execute(argv: any) {
    let rsp: any;

    if (argv._[0] === 'ls') {
      rsp = await ls(this.client)(argv.path);
    } else if (argv._[0] === 'mkdir') {
      rsp = await mkdir(this.client)(argv.path);
    } else if (argv._[0] === '') {
    }

    console.log(rsp);
  }
}
