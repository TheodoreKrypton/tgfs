import * as fs from 'fs';
import yargs from 'yargs/yargs';

import { Client } from 'src/api';
import { createDir } from 'src/api/ops/create-dir';
import { uploadBytes } from 'src/api/ops';
import { list } from 'src/api/ops/list';
import { removeDir } from 'src/api/ops/remove-dir';
import { Executor } from 'src/commands/executor';
import { parser } from 'src/commands/parser';
import { TGFSDirectory } from 'src/model/directory';

import { createClient } from '../utils/mock-tg-client';

const parse = () => {
  const argv = parser(yargs(process.argv)).argv;
  return argv;
};

describe('commands', () => {
  let client: Client;
  let executor: Executor;

  beforeAll(async () => {
    console.log = jest.fn();

    client = await createClient();

    executor = new Executor(client);
  });

  describe('ls', () => {
    afterEach(async () => {
      await removeDir(client)('/', true);
    });

    it('should list files and directories', async () => {
      await uploadBytes(client)(Buffer.from(''), '/f1');
      await createDir(client)('/d1', false);

      jest.replaceProperty(process, 'argv', ['ls', '/']);
      await executor.execute(parse());
      expect(console.log).toHaveBeenCalledWith('d1  f1');
    });

    it('should throw an error if path does not exist', () => {
      jest.replaceProperty(process, 'argv', ['ls', '/not-exist']);
      expect(executor.execute(parse())).rejects.toThrowError();
    });
  });

  describe('mkdir', () => {
    afterEach(async () => {
      await removeDir(client)('/', true);
    });

    it('should create a directory', async () => {
      jest.replaceProperty(process, 'argv', ['mkdir', '/d1']);
      await executor.execute(parse());

      const d1 = (await list(client)('/'))[0];
      expect(d1.name).toEqual('d1');
    });

    it('should create a directory recursively', async () => {
      jest.replaceProperty(process, 'argv', ['mkdir', '/d1/d2/d3', '-p']);
      await executor.execute(parse());

      const d3 = ((await list(client)('/d1/d2')) as Array<TGFSDirectory>)[0];

      expect(d3.name).toEqual('d3');
    });

    it('should throw an error if path already exists', async () => {
      jest.replaceProperty(process, 'argv', ['mkdir', '/d1']);
      await executor.execute(parse());

      jest.replaceProperty(process, 'argv', ['mkdir', '/d1']);
      expect(executor.execute(parse())).rejects.toThrowError();
    });
  });

  describe('cp', () => {
    afterEach(async () => {
      await removeDir(client)('/', true);
    });

    it('should upload a file', async () => {
      const fileName = 'mock-file.txt';

      fs.writeFileSync(fileName, 'mock-file-content');
      jest.replaceProperty(process, 'argv', ['cp', fileName, '/f1']);
      await executor.execute(parse());

      const f1 = client.getRootDirectory().findFiles(['f1'])[0];
      expect(f1.name).toEqual('f1');

      fs.unlinkSync('./mock-file.txt');
    });

    it('should throw an error if file does not exist', () => {
      jest.replaceProperty(process, 'argv', ['cp', 'not-exist', '/f1']);
      expect(executor.execute(parse())).rejects.toThrowError();
    });
  });

  describe('rm', () => {
    afterEach(async () => {
      await removeDir(client)('/', true);
    });

    it('should remove a file', async () => {
      await client.putFileUnder(
        'f1',
        client.getRootDirectory(),
        Buffer.from('content'),
      );

      jest.replaceProperty(process, 'argv', ['rm', '/f1']);
      await executor.execute(parse());

      expect(client.getRootDirectory().findFiles(['f1']).length).toEqual(0);
    });

    it('should remove a directory', async () => {
      await client.createDirectoryUnder('d1', client.getRootDirectory());

      jest.replaceProperty(process, 'argv', ['rm', '/d1']);
      await executor.execute(parse());

      expect(client.getRootDirectory().findChildren(['d1']).length).toEqual(0);
    });

    it('should throw an error if path does not exist', () => {
      jest.replaceProperty(process, 'argv', ['rm', '/not-exist']);
      expect(executor.execute(parse())).rejects.toThrowError();
    });

    it('should throw an error if trying to remove a directory that is not empty', async () => {
      const d1 = await client.createDirectoryUnder(
        'd1',
        client.getRootDirectory(),
      );
      await client.putFileUnder('f1', d1, Buffer.from('content'));

      jest.replaceProperty(process, 'argv', ['rm', '/d1']);
      expect(executor.execute(parse())).rejects.toThrowError();
    });

    it('should remove a directory recursively', async () => {
      jest.replaceProperty(process, 'argv', ['mkdir', '/d1/d2/d3', '-p']);
      await executor.execute(parse());

      jest.replaceProperty(process, 'argv', ['rm', '/d1', '-r']);
      await executor.execute(parse());

      expect(client.getRootDirectory().findChildren(['d1']).length).toEqual(0);
    });
  });
});
