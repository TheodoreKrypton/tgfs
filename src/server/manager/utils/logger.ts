import { Context } from 'src/server/manager/model/context';
import { Logger as BaseLogger } from 'src/utils/logger';

export class Logger extends BaseLogger {
  static override prefix() {
    return '[Manager]';
  }

  static ctx(ctx: Context) {
    return new LoggerWithContext(ctx);
  }
}

export class LoggerWithContext {
  constructor(private readonly ctx: Context) {}

  fmtCtx() {
    return `[${this.ctx.id}] [${this.ctx.user ?? '-'}]`;
  }

  info(...args: any[]) {
    Logger.info(this.fmtCtx(), ...args);
  }

  error(err: string | Error) {
    console.error(
      `[${Logger.getTime()}] [ERROR] ${Logger.prefix()} ${this.fmtCtx()} ${Logger.errorMsg(
        err,
      )}`,
    );
  }
}
