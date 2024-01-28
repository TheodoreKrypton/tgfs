import request from 'supertest';

import http from 'http';
import { v2 as webdav } from 'webdav-server';

import { TGFSFileSystem } from 'src/server/webdav/tgfs-filesystem';

import { createMockClient } from '../utils/mock-tg-client';

describe('TGFSFileSystem', () => {
  let server: http.Server;

  beforeAll(async () => {
    const mockClient = await createMockClient();
    const webDAVServer = new webdav.WebDAVServer();
    webDAVServer.setFileSystemSync('/', new TGFSFileSystem(mockClient));
    webDAVServer.start((httpServer) => {
      server = httpServer;
    });
  });

  describe('list directory', () => {
    it('should list root directory', async () => {
      const rsp = await request(server).propfind('/');
      expect(rsp.statusCode).toEqual(207);
    });

    it('should report 404 for non-exist directory', async () => {
      const rsp = await request(server).propfind('/non-exist');
      expect(rsp.statusCode).toEqual(404);
    });
  });

  describe('create directory', () => {
    it('should create a directory', async () => {
      const rsp = await request(server).mkcol('/d1');
      expect(rsp.statusCode).toEqual(201);
      const rsp2 = await request(server).propfind('/d1');
      expect(rsp2.statusCode).toEqual(207);
    });

    it('should report 405 for directory that already exists', async () => {
      const rsp = await request(server).mkcol('/d2');
      expect(rsp.statusCode).toEqual(201);
      const rsp2 = await request(server).mkcol('/d2');
      expect(rsp2.statusCode).toEqual(405);
    });

    it('should report 500 if the directory name is illegal', async () => {
      const rsp = await request(server).mkcol('/-d1');
      expect(rsp.statusCode).toEqual(500);
    });
  });

  describe('delete directory', () => {
    it('should delete a directory', async () => {
      await request(server).delete('/d1');
      const rsp = await request(server).propfind('/d1');
      expect(rsp.statusCode).toEqual(404);
    });

    it('should report 404 for non-exist directory', async () => {
      const rsp = await request(server).delete('/non-exist');
      expect(rsp.statusCode).toEqual(404);
    });
  });

  describe('upload file', () => {
    it('should upload a file', async () => {
      await request(server)
        .put('/f1')
        .set('Content-Type', 'text/plain')
        .send('mock-file-content')
        .expect(201);
      const rsp = await request(server).propfind('/f1');
      expect(rsp.statusCode).toEqual(207);
    });

    it('should show the file', async () => {
      const rsp = await request(server).propfind('/');
      expect(rsp.text).toEqual(expect.stringContaining('f1'));
    });

    it('should upload a file with overwrite', async () => {
      await request(server)
        .put('/f1')
        .set('Content-Type', 'text/plain')
        .send('mock-file-content');
      const rsp = await request(server).propfind('/f1');
      expect(rsp.statusCode).toEqual(207);
    });

    it('should create an empty file', async () => {
      await request(server)
        .put('/f2')
        .set('Content-Type', 'text/plain')
        .send('')
        .expect(201);
      const rsp = await request(server).propfind('/f2');
      expect(rsp.statusCode).toEqual(207);
    });

    it('should report 409 for non-exist directory', async () => {
      const rsp = await request(server)
        .put('/non-exist/f1')
        .set('Content-Type', 'text/plain')
        .send('mock-file-content');
      expect(rsp.statusCode).toEqual(409);
    });
  });

  describe('download file', () => {
    it('should download a file', async () => {
      const rsp = await request(server).get('/f1');
      expect(rsp.statusCode).toEqual(200);
      expect(rsp.body.toString()).toEqual('mock-file-content');
    });
  });

  describe('delete file', () => {
    it('should delete a file', async () => {
      await request(server).delete('/f1');
      const rsp = await request(server).propfind('/f1');
      expect(rsp.statusCode).toEqual(404);
    });

    it('should report 404 for non-exist file', async () => {
      const rsp = await request(server).delete('/non-exist');
      expect(rsp.statusCode).toEqual(404);
    });
  });
});
