import { TelegramClient } from 'telegram';

import { Client } from 'src/api';

const createClient = async () => {
  const client = new Client(
    new TelegramClient('mock-session', 0, 'mock-api-hash', {}),
    'mock-private-channel-id',
    'mock-public-channel-id',
  );
  await client.init();
  return client;
};

describe('file and directory operations', () => {
  describe('create / remove directories', () => {
    it('should create a directory', async () => {
      const client = await createClient();
      const root = client.getRootDirectory();
      const d1 = await client.createDirectoryUnder('d1', root);
      expect(root.findChildren(['d1'])[0]).toEqual(d1);
    });

    it('should remove a directory', async () => {
      const client = await createClient();
      const root = client.getRootDirectory();

      const d1 = await client.createDirectoryUnder('d1', root);
      await client.deleteDirectory(d1);
      expect(root.findChildren(['d1'])[0]).toBeUndefined();
    });

    it('should remove all directories', async () => {
      const client = await createClient();

      const d1 = await client.createDirectoryUnder(
        'd1',
        client.getRootDirectory(),
      );
      await client.createDirectoryUnder('d2', d1);
      await client.deleteDirectory(client.getRootDirectory());
      expect(client.getRootDirectory().findChildren(['d1'])[0]).toBeUndefined();
    });
  });

  describe('create / remove files', () => {
    it('should create a file', async () => {
      const client = await createClient();
      const root = client.getRootDirectory();
      const f1 = await client.putFileUnder(
        'f1',
        root,
        Buffer.from('mock-file-content'),
      );
      expect(root.findFiles(['f1'])[0]).toEqual(f1);
    });

    it('should add a file version', async () => {
      const client = await createClient();
      const root = client.getRootDirectory();
      await client.putFileUnder('f1', root, Buffer.from('mock-file-content'));

      const content2 = 'mock-file-content-edited';

      await client.putFileUnder('f1', root, Buffer.from(content2));
      const fr = root.findFiles(['f1'])[0];
      const f = await client.getFileInfo(fr);
      expect(Object.keys(f.versions)).toHaveLength(2);
      const content = await client.downloadFileAtVersion(fr);
      expect(content.toString()).toEqual(content2);
    });

    it('should edit a file version', async () => {
      const client = await createClient();
      const root = client.getRootDirectory();

      await client.putFileUnder('f1', root, Buffer.from('mock-file-content'));
      const content2 = 'mock-file-content-edited';
      const fr = root.findFiles(['f1'])[0];
      const f = await client.getFileInfo(fr);
      await client.updateFile(fr, Buffer.from(content2), f.latestVersionId);

      const content = await client.downloadFileAtVersion(fr);
      expect(content.toString()).toEqual(content2);
    });

    it('should remove a file', async () => {
      const client = await createClient();
      const root = client.getRootDirectory();

      const f1 = await client.putFileUnder(
        'f1',
        root,
        Buffer.from('mock-file-content'),
      );

      await client.deleteFileAtVersion(f1);
      expect(root.findFiles(['f1'])[0]).toBeUndefined();
    });

    it('should remove a file version', async () => {
      const client = await createClient();
      const root = client.getRootDirectory();
      const content = 'mock-file-content';
      await client.putFileUnder('f1', root, Buffer.from(content));

      await client.putFileUnder(
        'f1',
        root,
        Buffer.from('mock-file-content-edited'),
      );

      const fr = root.findFiles(['f1'])[0];
      let f = await client.getFileInfo(fr);

      await client.deleteFileAtVersion(fr, f.latestVersionId);

      f = await client.getFileInfo(fr);

      expect(Object.keys(f.versions)).toHaveLength(1);
      const content2 = await client.downloadFileAtVersion(fr);
      expect(content2.toString()).toEqual(content);
    });
  });
});
