import express, { Response } from 'express';

import { v4 as uuid } from 'uuid';

import { TechnicalError } from 'src/errors/base';

import { Auth } from './auth';
import { manager } from './db';
import { Request } from './model/request';
import { Logger } from './utils/logger';

const app = express();

const autoCatch = (
  fn: (
    req: Request,
    res: Response,
    next: (err?: Error) => void,
  ) => void | Promise<void>,
) => {
  return async (req: Request, res: Response, next: (err?: Error) => void) => {
    try {
      await fn(req, res, next);
    } catch (err) {
      next(err);
    }
  };
};

app.use(express.json());

app.use((req: Request & { reqId: string }, res, next) => {
  req.id = uuid();
  req.logger = Logger.ctx(req);
  req.logger.info(req.method, req.path);
  req.auth = new Auth(req);
  next();
});

// set cors headers
app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', '*');
  res.header('Access-Control-Allow-Methods', 'DELETE, POST, GET, OPTIONS');
  res.header('Access-Control-Allow-Headers', 'content-type, authorization');
  res.header('Access-Control-Allow-Credentials', 'true');
  next();
});

app.use(
  autoCatch(async (req: Request, res, next) => {
    if (req.method === 'OPTIONS') {
      next();
    } else if (req.method === 'POST' && req.path === '/login') {
      next();
    } else {
      const token = req.headers.authorization.replace('Bearer ', '');
      req.auth = new Auth(req);
      await req.auth.authenticate(token);
      next();
    }
  }),
);

app.options('*', (req, res, next) => {
  res.status(200);
  next();
});

app.post(
  '/login',
  autoCatch(async (req, res, next) => {
    const token = await req.auth.generateToken(
      req.body.username,
      req.body.password,
    );
    res.write(token);
    next();
  }),
);

app.get(
  '/tasks',
  autoCatch(async (req, res, next) => {
    res.write(manager.getTasks());
    next();
  }),
);

app.use(
  (err: Error, req: Request, res: Response, next: (err?: Error) => void) => {
    req.logger.error(err);
    next(err);
  },
);

app.use(
  (err: Error, req: Request, res: Response, next: (err?: Error) => void) => {
    if (err instanceof TechnicalError) {
      const error = new err.httpError(err.message);
      res.status(error.statusCode);
    } else {
      res.status(500);
    }
    next();
  },
);

app.use((req: Request, res) => {
  req.logger.info(res.statusCode);
  res.send();
});

export const managerServer = app;
T