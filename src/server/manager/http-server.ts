import express from 'express';

import { db } from './db';

const app = express();

// set cors headers
app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', '*');
  next();
});

app.get('/tasks', (req, res) => {
  console.log(db.getTasks());
  res.send(db.getTasks());
});

export const managerServer = app;
