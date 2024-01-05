import HTTPErrors from 'http-errors';

import { BusinessError } from './base';

export class BadAuthentication extends BusinessError {
  constructor(
    public readonly message: string,
    public readonly cause?: string,
  ) {
    super(message, 'BAD_AUTHENTICATION', cause, HTTPErrors.Unauthorized);
  }
}

export class MissingAuthenticationHeaders extends BadAuthentication {
  constructor() {
    super('Missing authentication headers', 'Missing authentication headers');
  }
}

export class InvalidCredentials extends BadAuthentication {
  constructor(public readonly cause: string) {
    super('Bad authentication', cause);
  }
}

export class UserNotFound extends InvalidCredentials {
  constructor(public readonly username: string) {
    super(`User ${username} not found`);
  }
}

export class IncorrectPassword extends InvalidCredentials {
  constructor(public readonly username: string) {
    super(`Password for ${username} does not match`);
  }
}

export class JWTInvalid extends InvalidCredentials {
  constructor() {
    super('JWT token invalid');
  }
}
