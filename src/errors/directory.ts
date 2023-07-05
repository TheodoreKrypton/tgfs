import { BusinessError } from './base';

export class DirectoryAlreadyExistsError extends BusinessError {
  constructor(public readonly dirName: string, public readonly cause?: string) {
    super(
      `Directory ${dirName} already exists`,
      'DIRECTORY_ALREADY_EXISTS',
      cause,
    );
  }
}
