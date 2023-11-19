import { v2 as webdav } from 'webdav-server';

import { Client } from 'src/api';
import { config } from 'src/config';
import { Logger } from 'src/utils/logger';

import { TGFSFileSystem } from './tgfs-filesystem';

class Authentication extends webdav.HTTPBasicAuthentication {
  getUser(
    ctx: webdav.HTTPRequestContext,
    callback: (error: Error, user: webdav.IUser) => void,
  ) {
    const cb = (error: Error, user: webdav.IUser) => {
      if (error) {
        callback(webdav.Errors.BadAuthentication, null);
      } else {
        callback(null, user);
      }
    };
    super.getUser(ctx, cb);
  }
}

export const webdavServer = (
  client: Client,
  options?: webdav.WebDAVServerOptions,
) => {
  const userManager = new webdav.SimpleUserManager();
  Object.keys(config.tgfs.users).forEach((user: string) => {
    userManager.addUser(user, config.tgfs.users[user].password, true);
  });

  const server = new webdav.WebDAVServer({
    ...options,
    httpAuthentication: new Authentication(userManager),
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
  return server;
};
