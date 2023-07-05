import { BusinessError, TechnicalError } from '../errors/base';

export class Logger {
  static error(err: string | Error) {
    if (err instanceof BusinessError) {
      console.error(
        `${new Date()} [ERROR] ${err.code} ${err.name} ${err.message}`,
      );
    } else if (err instanceof TechnicalError) {
      console.error(
        `${new Date()} [ERROR] ${err.name} ${err.message} ${err.cause}\n${
          err.stack
        }`,
      );
    } else if (err instanceof Error) {
      console.error(
        `${new Date()} [ERROR] ${err.name} ${err.message}\n${err.stack}`,
      );
    } else {
      console.error(`${new Date()} [ERROR] ${err}`);
    }
  }
}
