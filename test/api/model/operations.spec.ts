import { sleep } from '../../../src/utils/sleep';
import { createClient } from '../../utils/mock-tg-client';

describe('file and directory operations', () => {
  describe('create / remove directories', () => {
    it('should create a directory', async () => {
      const client = await createClient();
      const root = client.getRootDirectory();
      const d1 = await client.createDirectory({ name: 'd1', under: root });
      expect(root.findChildren(['d1'])[0]).toEqual(d1);
    });

    it('should remove a directory', async () => {
      const client = await createClient();
      const root = client.getRootDirectory();

      const d1 = await client.createDirectory({ name: 'd1', under: root });
      await client.dangerouslyDeleteDirectory(d1);
      expect(root.findChildren(['d1'])[0]).toBeUndefined();
    });

    it('should remove all directories', async () => {
      const client = await createClient();

      const d1 = await client.createDirectory({
        name: 'd1',
        under: client.getRootDirectory(),
      });
      await client.createDirectory({ name: 'd2', under: d1 });
      await client.dangerouslyDeleteDirectory(client.getRootDirectory());
      expect(client.getRootDirectory().findChildren(['d1'])[0]).toBeUndefined();
    });
  });

  describe('create / remove files', () => {
    it('should create a file', async () => {
      const client = await createClient();
      const root = client.getRootDirectory();
      const f1 = await client.uploadFile(
        { name: 'f1', under: root },
        Buffer.from('mock-file-content'),
      );
      expect(root.findFiles(['f1'])[0]).toEqual(f1);
    });

    it('should add a file version', async () => {
      const client = await createClient();
      const root = client.getRootDirectory();
      await client.uploadFile(
        { name: 'f1', under: root },
        Buffer.from('mock-file-content'),
      );

      await sleep(300);
      const content2 = 'mock-file-content-edited';
      await client.uploadFile(
        { name: 'f1', under: root },
        Buffer.from(content2),
      );
      const fr = root.findFiles(['f1'])[0];
      const fd = await client.getFileDesc(fr);
      expect(Object.keys(fd.versions)).toHaveLength(2);
      const content = await client.downloadFileVersion(fd.getLatest(), 'f1');
      expect(content.toString()).toEqual(content2);
    });

    it('should edit a file version', async () => {
      const client = await createClient();
      const root = client.getRootDirectory();

      await client.uploadFile(
        { name: 'f1', under: root },
        Buffer.from('mock-file-content'),
      );

      const content2 = 'mock-file-content-edited';
      const fr = root.findFiles(['f1'])[0];
      const fd = await client.getFileDesc(fr);

      await client.uploadFile(
        { name: 'f1', under: root, versionId: fd.latestVersionId },
        Buffer.from(content2),
      );

      const newFd = await client.getFileDesc(fr);

      const content = await client.downloadFileVersion(newFd.getLatest(), 'f1');
      expect(content.toString()).toEqual(content2);
    });

    it('should remove a file', async () => {
      const client = await createClient();
      const root = client.getRootDirectory();

      const f1 = await client.uploadFile(
        { name: 'f1', under: root },
        Buffer.from('mock-file-content'),
      );

      await client.deleteFile(f1);
      expect(root.findFiles(['f1'])[0]).toBeUndefined();
    });

    it('should remove a file version', async () => {
      const client = await createClient();
      const root = client.getRootDirectory();
      const content = 'mock-file-content';
      await client.uploadFile(
        { name: 'f1', under: root },
        Buffer.from(content),
      );
      await sleep(300);
      await client.uploadFile(
        { name: 'f1', under: root },
        Buffer.from('mock-file-content-edited'),
      );

      const fr = root.findFiles(['f1'])[0];
      let f = await client.getFileDesc(fr);

      await client.deleteFile(fr, f.latestVersionId);

      f = await client.getFileDesc(fr);
      expect(Object.keys(f.versions)).toHaveLength(1);
      const fd = await client.getFileDesc(fr);
      const fv = fd.getLatest();
      const content2 = await client.downloadFileVersion(fv, 'f1');
      expect(content2.toString()).toEqual(content);
    });
  });
});
