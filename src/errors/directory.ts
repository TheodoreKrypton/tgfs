import { BusinessError } from './base';

export class DirectoryAlreadyExistsError extends BusinessError {
  constructor(public readonly dirName: string, public readonly cause?: string) {
    super(`Directory ${dirName} already exists`, 'DIR_ALREADY_EXISTS', cause);
  }
}

export class FileOrDirectoryDoesNotExistError extends BusinessError {
  constructor(public readonly dirName: string, public readonly cause?: string) {
    super(
      `No such file or directory: ${dirName}`,
      'FILE_OR_DIR_DOES_NOT_EXIST',
      cause,
    );
  }
}
