import fs from 'fs';

import { Client } from 'src/api';
import { saveToBuffer, saveToFile } from 'src/api/utils';
import { Logger } from 'src/utils/logger';
import { sleep } from 'src/utils/sleep';

import { createMockClient } from '../../mock/mock-tg-client';

describe('file and directory operations', () => {
  beforeAll(() => {
    Logger.info = jest.fn();
  });

  describe('create / remove directories', () => {
    let client: Client;

    beforeEach(async () => {
      client = await createMockClient();
    });

    it('should create a directory', async () => {
      const root = client.dir.root();
      const d1 = await client.dir.create({ name: 'd1', under: root });
      expect(root.findDirs(['d1'])[0]).toEqual(d1);
    });

    it('should throw an error if the directory name is illegal', async () => {
      const root = client.dir.root();

      await expect(
        client.dir.create({ name: '-d1', under: root }),
      ).rejects.toThrow();
      await expect(
        client.dir.create({ name: 'd/1', under: root }),
      ).rejects.toThrow();
    });

    it('should remove a directory', async () => {
      const root = client.dir.root();

      const d1 = await client.dir.create({ name: 'd1', under: root });
      await client.dir.rmDangerously(d1);
      expect(root.findDirs(['d1'])[0]).toBeUndefined();
    });

    it('should remove all directories', async () => {
      const d1 = await client.dir.create({
        name: 'd1',
        under: client.dir.root(),
      });
      await client.dir.create({ name: 'd2', under: d1 });
      await client.dir.rmDangerously(client.dir.root());
      expect(client.dir.root().findDirs(['d1'])[0]).toBeUndefined();
    });
  });

  describe('create / remove files', () => {
    let client: Client;

    beforeEach(async () => {
      client = await createMockClient();
    });

    it('should create a small file from buffer', async () => {
      const root = client.dir.root();
      const f1 = await client.file.upload(
        { under: root },
        { name: 'f1', buffer: Buffer.from('mock-file-content') },
      );
      expect(root.findFiles(['f1'])[0]).toEqual(f1);
    });

    it('should create a small file from path', async () => {
      const fileName = `${Math.random()}.txt`;
      fs.writeFileSync(fileName, 'mock-file-content');

      const root = client.dir.root();
      const f1 = await client.file.upload(
        { under: root },
        { name: 'f1', path: fileName },
      );
      expect(root.findFiles(['f1'])[0]).toEqual(f1);

      fs.rmSync(fileName);
    });

    it('should create a big file from buffer', async () => {
      const content = Buffer.alloc(1024 * 1024 * 10, 'a');

      const root = client.dir.root();

      const f1 = await client.file.upload(
        { under: root },
        { name: 'f1', buffer: content },
      );
      expect(root.findFiles(['f1'])[0]).toEqual(f1);
    });

    it('should create a big file from path', async () => {
      const fileName = `${Math.random()}.txt`;
      const content = Buffer.alloc(1024 * 1024 * 10, 'a');
      fs.writeFileSync(fileName, content);

      const root = client.dir.root();

      const f1 = await client.file.upload(
        { under: root },
        { name: 'f1', path: fileName },
      );
      expect(root.findFiles(['f1'])[0]).toEqual(f1);

      fs.rmSync(fileName);
    });

    it('should add a file version', async () => {
      const root = client.dir.root();
      await client.file.upload(
        { under: root },
        { name: 'f1', buffer: Buffer.from('mock-file-content') },
      );

      await sleep(300); // wait for the timestamp to change to ensure the order of versions
      const content2 = 'mock-file-content-edited';
      await client.file.upload(
        { under: root },
        { name: 'f1', buffer: Buffer.from(content2) },
      );
      const fr = root.findFiles(['f1'])[0];
      const fd = await client.file.desc(fr);
      expect(Object.keys(fd.versions)).toHaveLength(2);
      const content = await saveToBuffer(client.file.retrieve(fr, 'f1'));
      expect(content.toString()).toEqual(content2);
    });

    it('should edit a file version', async () => {
      const root = client.dir.root();

      await client.file.upload(
        { under: root },
        { name: 'f1', buffer: Buffer.from('mock-file-content') },
      );

      const content2 = 'mock-file-content-edited';
      let fr = root.findFiles(['f1'])[0];
      const fd = await client.file.desc(fr);

      await client.file.upload(
        { under: root, versionId: fd.latestVersionId },
        { name: 'f1', buffer: Buffer.from(content2) },
      );

      const content = await saveToBuffer(client.file.retrieve(fr, 'f1'));
      expect(content.toString()).toEqual(content2);
    });

    // it('should not reupload the original file', async () => {
    //   const client = await createClient();
    //   const root = client.getRootDirectory();

    //   const content = 'original file content to test reupload of a same file';

    //   await client.uploadFile(
    //     { name: 'f1', under: root },
    //     Buffer.from(content),
    //   );

    //   await client.uploadFile(
    //     { name: 'f2', under: root },
    //     Buffer.from(content),
    //   );
    // });

    it('should remove a file', async () => {
      const root = client.dir.root();

      const f1 = await client.file.upload(
        { under: root },
        { name: 'f1', buffer: Buffer.from('mock-file-content') },
      );

      const fr = root.findFiles(['f1'])[0];
      await client.file.rm(fr);
      expect(root.findFiles(['f1'])[0]).toBeUndefined();
    });

    it('should remove a file version', async () => {
      const root = client.dir.root();
      const content = 'mock-file-content';
      await client.file.upload(
        { under: root },
        { name: 'f1', buffer: Buffer.from(content) },
      );
      await sleep(300);
      await client.file.upload(
        { under: root },
        { name: 'f1', buffer: Buffer.from('mock-file-content-edited') },
      );

      const fr = root.findFiles(['f1'])[0];
      let fd = await client.file.desc(fr);

      await client.file.rm(fr, fd.latestVersionId);

      fd = await client.file.desc(fr);
      expect(Object.keys(fd.versions)).toHaveLength(1);
      const content2 = await saveToBuffer(client.file.retrieve(fr, 'f1'));
      expect(content2.toString()).toEqual(content);
    });

    it('should download a file as a local file', async () => {
      const root = client.dir.root();
      const content = 'mock-file-content';
      await client.file.upload(
        { under: root },
        { name: 'f1', buffer: Buffer.from(content) },
      );

      const fr = root.findFiles(['f1'])[0];
      const localFileName = `${Math.random()}.txt`;

      await saveToFile(client.file.retrieve(fr, 'f1'), localFileName);

      const contentRead = fs.readFileSync(localFileName);
      expect(contentRead.toString()).toEqual(content);

      fs.rmSync(localFileName);
    });
  });
});
