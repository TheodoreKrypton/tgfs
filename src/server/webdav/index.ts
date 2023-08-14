import { v2 as webdav } from 'webdav-server';
import { PhysicalFileSystem } from 'webdav-server/lib/index.v2';

import { Client } from '../../api';
import { config } from '../../config';
import { Logger } from '../../utils/logger';
import { TGFSFileSystem } from './tgfs-filesystem';

export const runWebDAVServer = async (
  client: Client,
  options?: webdav.WebDAVServerOptions,
) => {
  const server = new webdav.WebDAVServer(options);

  server.httpAuthentication = new webdav.HTTPBasicAuthentication({
    getUserByNamePassword: (username, password, cb) => {
      const user = config.webdav.users[username];
      if (user && user.password === password) {
        cb(null, { uid: username, username });
      } else {
        cb(webdav.Errors.UserNotFound);
      }
    },
    getDefaultUser(cb) {
      cb(null);
    },
  });

  server.beforeRequest((ctx, next) => {
    Logger.info(ctx.request.method, ctx.requested.uri);
    next();
  });
  server.afterRequest((ctx, next) => {
    Logger.info(ctx.request.method, ctx.response.statusCode);
    next();
  });
  server.setFileSystemSync('/', new TGFSFileSystem(client));

  server.start((httpServer) => {
    const address = httpServer.address() as any;
    Logger.info(
      `WebDAV server is running on ${address.address}:${address.port}`,
    );
  });
};
