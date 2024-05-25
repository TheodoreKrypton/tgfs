import { writeFileSync } from 'fs';

import { generateRandomBytes, readBigIntFromBuffer } from 'telegram/Helpers';

export { getAppropriatedPartSize } from 'telegram/Utils';

export const generateFileId = () => {
  return readBigIntFromBuffer(generateRandomBytes(8), true, true);
};

export const saveToBuffer = async (
  generator: AsyncGenerator<Buffer>,
): Promise<Buffer> => {
  const buffers: Buffer[] = [];
  for await (const chunk of generator) {
    buffers.push(chunk);
  }
  return Buffer.concat(buffers);
};

export const saveToFile = async (
  generator: AsyncGenerator<Buffer>,
  path: string,
): Promise<void> => {
  const content = await saveToBuffer(generator);
  writeFileSync(path, content);
};
