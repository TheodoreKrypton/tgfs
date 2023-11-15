import express from 'express';

import { db } from './db';

const app = express();

app.get('/tasks', (req, res) => {
  return db.getTasks();
});

export const managerServer = app;
