import { TGFSDirectory } from 'src/model/directory';

describe('serialization and deserialization of directory', () => {
  it('should equal to the original directory', () => {
    const directory = {
      type: 'TGFSDirectory',
      name: 'test',
      children: [
        {
          type: 'TGFSDirectory',
          name: 'test-sub1',
          children: [],
          files: [],
        },
        {
          type: 'TGFSDirectory',
          name: 'test-sub2',
          children: [
            {
              type: 'TGFSDirectory',
              name: 'test-sub2-sub1',
              children: [],
              files: [
                {
                  type: 'TGFSFileRef',
                  name: 'test-sub2-sub1-file1',
                  messageId: 2,
                },
              ],
            },
          ],
          files: [],
        },
      ],
      files: [
        {
          type: 'TGFSFileRef',
          name: 'test-file1',
          messageId: 1,
        },
      ],
    } as any;

    expect(TGFSDirectory.fromObject(directory).toObject()).toEqual(directory);
  });
});
