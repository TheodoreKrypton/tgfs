import chokidar from 'chokidar';

import { config } from '../config';

export const runSync = () => {
  Object.values(config.sync).forEach((sync: { local: string }) => {
    chokidar.watch(sync.local).on('all', (event, path) => {
      console.log(event, path);
    });
  });
};
