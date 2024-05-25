import { AggregatedError, BusinessError, TechnicalError } from '../errors/base';

export class Logger {
  static tzOffset = new Date().getTimezoneOffset() * 60000;

  static prefix() {
    return '[TGFS]';
  }

  static getTime() {
    return new Date(Date.now() - this.tzOffset).toISOString().slice(0, -1);
  }

  static debug(...args: any[]) {
    if (process.env.DEBUG === 'true') {
      console.debug(`[${this.getTime()}] [DEBUG] ${this.prefix()}`, ...args);
    }
  }

  static info(...args: any[]) {
    console.info(`[${this.getTime()}] [INFO]  ${this.prefix()}`, ...args);
  }

  static errorMsg(err: string | Error) {
    if (err instanceof AggregatedError) {
      err.errors.forEach((e) => this.errorMsg(e));
    } else if (err instanceof BusinessError) {
      return `${err.code} (message: ${err.message} \n${err.stack}) (cause: ${err.cause})`;
    } else if (err instanceof TechnicalError) {
      return `Technical Error: (message: ${err.message}) (cause: ${err.cause})\n${err.stack})`;
    } else if (err instanceof Error) {
      return `${err.name} ${err.message}\n${err.stack}`;
    } else {
      return `${this.prefix()} ${err}`;
    }
  }

  static error(err: string | Error) {
    console.error(
      `[${this.getTime()}] [ERROR] ${this.prefix()} ${this.errorMsg(err)}`,
    );
  }

  static stdout(...args: any[]) {
    console.log(...args);
  }
}
