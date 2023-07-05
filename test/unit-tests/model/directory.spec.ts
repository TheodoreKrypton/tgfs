import { TGFSDirectory } from 'src/model/directory';

describe('serialization and deserialization of directory', () => {
  it('should equal to the original directory', () => {
    const directory = {
      name: 'test',
      children: [
        {
          name: 'test-sub1',
          children: [],
          files: [],
        },
        {
          name: 'test-sub2',
          children: [
            {
              name: 'test-sub2-sub1',
              children: [],
              files: [{ name: 'test-sub2-sub1-file1', messageId: 2 }],
            },
          ],
          files: [],
        },
      ],
      files: [
        {
          name: 'test-file1',
          messageId: 1,
        },
      ],
    } as any;

    expect(TGFSDirectory.fromObject(directory).toObject()).toEqual(directory);
  });
});
