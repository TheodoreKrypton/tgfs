import { BusinessError } from './base';

export class FileIsEmptyError extends BusinessError {
  constructor(
    public readonly filename: string,
    public readonly cause?: string,
  ) {
    super(`File ${filename} is empty`, 'FILE_IS_EMPTY', cause);
  }
}

export class FileAlreadyExistsError extends BusinessError {
  constructor(
    public readonly fileName: string,
    public readonly cause?: string,
  ) {
    super(`File ${fileName} already exists`, 'FILE_ALREADY_EXISTS', cause);
  }
}
