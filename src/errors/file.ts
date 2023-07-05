import { BusinessError } from './base';

export class FileIsEmptyError extends BusinessError {
  constructor(
    public readonly filename: string,
    public readonly cause?: string,
  ) {
    super(`File ${filename} is empty`, 'FILE_IS_EMPTY', cause);
  }
}
