import { v2 as webdav } from 'webdav-server';

import { loginAsBot } from '../../auth';
import { TGFSFileSystem } from './tgfs-filesystem';

(async () => {
  const server = new webdav.WebDAVServer();

  const client = await loginAsBot();
  await client.init();

  server.setFileSystemSync('/', new TGFSFileSystem(client));

  server.start((httpServer) => {
    console.log(
      'Server started with success on the port : ' +
        (httpServer.address() as any).port,
    );
  });
})();
