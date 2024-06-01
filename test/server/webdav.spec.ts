import express from 'express';
import supertest from 'supertest';

import { v2 as webdav } from 'webdav-server';

import { TGFSFileSystem } from 'src/server/webdav/tgfs-filesystem';
import { Logger } from 'src/utils/logger';

import { createMockClient } from '../utils/mock-tg-client';

describe('TGFSFileSystem', () => {
  const getServer = async () => {
    const mockClient = await createMockClient();
    const webDAVServer = new webdav.WebDAVServer();

    webDAVServer.setFileSystemSync('/', new TGFSFileSystem(mockClient));
    const app = express();

    return supertest(app.use(webdav.extensions.express('/', webDAVServer)));
  };

  beforeAll(() => {
    Logger.info = jest.fn();
  });

  describe('list directory', () => {
    it('should list root directory', async () => {
      const server = await getServer();
      const rsp = await server.propfind('/');
      expect(rsp.statusCode).toEqual(207);
    });

    it('should report 404 for non-exist directory', async () => {
      const server = await getServer();
      const rsp = await server.propfind('/non-exist');
      expect(rsp.statusCode).toEqual(404);
    });
  });

  describe('create directory', () => {
    it('should create a directory', async () => {
      const server = await getServer();
      const rsp = await server.mkcol('/d1');
      expect(rsp.statusCode).toEqual(201);
      const rsp2 = await server.propfind('/d1');
      expect(rsp2.statusCode).toEqual(207);
    });

    it('should report 405 for directory that already exists', async () => {
      const server = await getServer();
      const rsp = await server.mkcol('/d2');
      expect(rsp.statusCode).toEqual(201);
      const rsp2 = await server.mkcol('/d2');
      expect(rsp2.statusCode).toEqual(405);
    });

    it('should report 500 if the directory name is illegal', async () => {
      const server = await getServer();
      const rsp = await server.mkcol('/-d1');
      expect(rsp.statusCode).toEqual(500);
    });
  });

  describe('delete directory', () => {
    it('should delete a directory', async () => {
      const server = await getServer();
      await server.delete('/d1');
      const rsp = await server.propfind('/d1');
      expect(rsp.statusCode).toEqual(404);
    });

    it('should report 404 for non-exist directory', async () => {
      const server = await getServer();
      const rsp = await server.delete('/non-exist');
      expect(rsp.statusCode).toEqual(404);
    });
  });

  const uploadFile = (
    server: supertest.SuperTest<supertest.Test>,
    path: string,
    content: string,
  ) => {
    return server
      .put(path)
      .set('Content-Type', 'text/plain')
      .send(Buffer.from(content));
  };

  describe('upload file', () => {
    it('should upload a file and show the file', async () => {
      const server = await getServer();
      await uploadFile(server, '/f1', 'mock-file-content').expect(201);
      const rsp = await server.propfind('/f1');
      expect(rsp.statusCode).toEqual(207);
      expect(rsp.text).toEqual(expect.stringContaining('f1'));
    });

    it('should upload a file with overwrite', async () => {
      const server = await getServer();
      await uploadFile(server, '/f1', 'mock-file-content').expect(201);
      await uploadFile(server, '/f1', 'edited-mock-file-content');
      const rsp = await server.propfind('/f1');
      expect(rsp.statusCode).toEqual(207);
    });

    it('should create an empty file', async () => {
      const server = await getServer();
      await uploadFile(server, '/f2', '').expect(201);
      const rsp = await server.propfind('/f2');
      expect(rsp.statusCode).toEqual(207);
    });

    it('should report 409 for non-exist directory', async () => {
      const server = await getServer();
      const rsp = await uploadFile(
        server,
        '/non-exist/f1',
        'mock-file-content',
      );
      expect(rsp.statusCode).toEqual(409);
    });
  });

  describe('download file', () => {
    it('should download a file', async () => {
      const server = await getServer();
      await uploadFile(server, '/f1', 'mock-file-content').expect(201);

      await server
        .get('/f1')
        .expect(200)
        .parse((res: supertest.Response, callback) => {
          callback(null, null);
        });

      // TODO: I don't know how to receive the data
    });
  });

  describe('delete file', () => {
    it('should delete a file', async () => {
      const server = await getServer();
      await server.delete('/f1');
      const rsp = await server.propfind('/f1');
      expect(rsp.statusCode).toEqual(404);
    });

    it('should report 404 for non-exist file', async () => {
      const server = await getServer();
      const rsp = await server.delete('/non-exist');
      expect(rsp.statusCode).toEqual(404);
    });
  });
});
