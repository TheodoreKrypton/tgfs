import express from 'express';

import { db } from './db';

const monitor = express();

monitor.get('/tasks', function (req, res) {
  res.send(db.getTasks());
});

export default monitor;
