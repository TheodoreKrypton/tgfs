import express, { Request, Response } from 'express';

import { BadAuthentication } from 'src/errors';
import { TechnicalError } from 'src/errors/base';

import { generateToken, verifyToken } from './auth';
import { db } from './db';

const app = express();

app.use(async (req, res, next) => {
  if (req.path === '/login') {
    next();
  }

  const token = req.headers['authorization'];
  if (token === undefined) {
    res.redirect('/');
  }

  try {
    await verifyToken(token);
  } catch (err) {
    res.redirect('/');
  }
});

// set cors headers
app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', '*');
  next();
});

app.post('/login', (req, res) => {
  const token = generateToken(req.body.username, req.body.password);
  res.setHeader('Set-Cookie', `token=${token}; HttpOnly`);
  res.end();
});

app.get('/tasks', (req, res) => {
  console.log(req.headers);
  res.send(db.getTasks());
});

app.use((err: Error, req: Request, res: Response, next: () => any) => {
  if (err instanceof TechnicalError) {
    const error = new err.httpError(err.message);
    res.status(error.statusCode).send(error.message);
  } else {
    res.status(500).send('Internal Server Error');
  }
});

export const managerServer = app;
