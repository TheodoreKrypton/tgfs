import { BusinessError } from './base';

export class UnknownCommandError extends BusinessError {
  constructor(command: string) {
    super(`Unknown command: ${command}`, 'UNKNOWN_COMMAND');
  }
}
