import { BusinessError } from './base';

export class FileOrDirectoryAlreadyExistsError extends BusinessError {
  constructor(
    public readonly name: string,
    public readonly cause?: string,
  ) {
    super(`${name} already exists`, 'FILE_OR_DIR_ALREADY_EXISTS', cause);
  }
}

export class FileOrDirectoryDoesNotExistError extends BusinessError {
  constructor(
    public readonly name: string,
    public readonly cause?: string,
  ) {
    super(
      `No such file or directory: ${name}`,
      'FILE_OR_DIR_DOES_NOT_EXIST',
      cause,
    );
  }
}

export class InvalidNameError extends BusinessError {
  constructor(
    public readonly name: string,
    public readonly cause?: string,
  ) {
    super(
      `Invalid name: ${name}. Name cannot begin with -, and cannot contain /`,
      'INVALID_NAME',
      cause,
    );
  }
}

export class RelativePathError extends BusinessError {
  constructor(
    public readonly name: string,
    public readonly cause?: string,
  ) {
    super(
      `Relative path: ${name} is not supported. Path must start with /`,
      'RELATIVE_PATH',
      cause,
    );
  }
}

export class DirectoryIsNotEmptyError extends BusinessError {
  constructor(public readonly cause?: string) {
    super(
      `Cannot remove a directory that is not empty`,
      'DIR_IS_NOT_EMPTY',
      cause,
    );
  }
}
