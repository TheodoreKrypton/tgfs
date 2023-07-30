import { v2 as webdav } from 'webdav-server';

import { Client } from '../../api';
import { TGFSFileSystem } from './tgfs-filesystem';

export const runWebDAVServer = async (
  client: Client,
  options?: webdav.WebDAVServerOptions,
) => {
  const server = new webdav.WebDAVServer(options);

  server.httpAuthentication = new webdav.HTTPBasicAuthentication({
    getUserByNamePassword: (username, password, cb) => {
      cb(null, { uid: username, username });
    },
    getDefaultUser(cb) {
      cb(null);
    },
  });
  server.setFileSystemSync('/', new TGFSFileSystem(client));
  server.start((httpServer) => {
    const address = httpServer.address() as any;
    console.info(
      `WebDAV server is running on ${address.address}:${address.port}`,
    );
  });
};
