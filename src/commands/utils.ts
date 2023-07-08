import { PathLike } from 'fs';

export const splitPath = (path: PathLike) => {
  const pathString = path.toString();

  if (!pathString.startsWith('/')) {
    throw new Error('Relative paths are not supported');
  }

  const parts = pathString.split('/');
  return [parts.slice(0, parts.length - 1).join('/'), parts[parts.length - 1]];
};
