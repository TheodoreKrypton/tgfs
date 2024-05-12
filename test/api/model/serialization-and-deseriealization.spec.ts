import { TGFSDirectory } from 'src/model/directory';

describe('serialization and deserialization', () => {
  it('should equal to the original directory', () => {
    const d1 = new TGFSDirectory('d1', null);
    const d2 = d1.createDir('d2');
    d2.createFileRef('f1', 1);

    expect(TGFSDirectory.fromObject(d1.toObject()).toObject()).toEqual(
      d1.toObject(),
    );
  });

  it('should equal to the expected structure', () => {
    const d1 = new TGFSDirectory('d1', null);
    const d2 = d1.createDir('d2');
    d2.createFileRef('f1', 1);

    expect(d1.toObject()).toEqual({
      name: 'd1',
      type: 'D',
      children: [
        {
          name: 'd2',
          type: 'D',
          children: [],
          files: [
            {
              name: 'f1',
              type: 'FR',
              messageId: 1,
            },
          ],
        },
      ],
      files: [],
    });
  });
});
