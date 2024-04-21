import { AggregatedError, BusinessError, TechnicalError } from '../errors/base';

export class Logger {
  static tzOffset = new Date().getTimezoneOffset() * 60000;

  static getTime() {
    return new Date(Date.now() - this.tzOffset).toISOString().slice(0, -1);
  }

  static debug(...args: any[]) {
    if (process.env.DEBUG === 'true') {
      console.debug(`[${this.getTime()}] [DEBUG]`, ...args);
    }
  }

  static info(...args: any[]) {
    console.info(`[${this.getTime()}] [INFO]`, ...args);
  }

  static error(err: string | Error) {
    if (err instanceof AggregatedError) {
      err.errors.forEach((e) => this.error(e));
    } else if (err instanceof BusinessError) {
      console.error(
        `[${this.getTime()}] [ERROR] ${err.code} ${err.name} ${err.message} \n${err.stack}`,
      );
    } else if (err instanceof TechnicalError) {
      console.error(
        `[${this.getTime()}] [ERROR] ${err.name} ${err.message} ${err.cause}\n${
          err.stack
        }`,
      );
    } else if (err instanceof Error) {
      console.error(
        `[${this.getTime()}] [ERROR] ${err.name} ${err.message}\n${err.stack}`,
      );
    } else {
      console.error(`[${this.getTime()}] [ERROR] ${err}`);
    }
  }
}
