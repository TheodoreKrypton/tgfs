import { PathLike } from 'fs';

import { RelativePathError } from '../../errors/path';

export const splitPath = (path: PathLike) => {
  const pathString = path.toString();

  if (!pathString.startsWith('/')) {
    throw new RelativePathError(pathString);
  }

  const parts = pathString.split('/');
  return [parts.slice(0, parts.length - 1).join('/'), parts[parts.length - 1]];
};
