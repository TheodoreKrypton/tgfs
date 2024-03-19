import { Request as _Request } from 'express';

import { Auth } from 'src/server/manager/auth';
import { Logger, LoggerWithContext } from 'src/server/manager/utils/logger';

import { Context } from './context';

export type Request = _Request &
  Context & {
    logger?: LoggerWithContext;
    auth?: Auth;
  };

