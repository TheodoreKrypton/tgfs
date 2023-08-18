import { InvalidNameError } from 'src/errors/path';

export const validateName = (name: string) => {
  if (name.startsWith('-') || name.includes('/')) {
    throw new InvalidNameError(name);
  }
};
