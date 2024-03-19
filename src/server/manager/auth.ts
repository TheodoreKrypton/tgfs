import jwt from 'jsonwebtoken';

import { config } from 'src/config';
import { IncorrectPassword, JWTInvalid, UserNotFound } from 'src/errors';
import { TechnicalError } from 'src/errors/base';

import { Context, WithContext } from './model/context';
import { LoggerWithContext } from './utils/logger';

type JWTPayload = {
  user: string;
  exp: number;
  iat: number;
};

export class Auth extends WithContext {
  private logger: LoggerWithContext;

  constructor(protected readonly context: Context) {
    super(context);

    this.logger = new LoggerWithContext(context);
  }

  private static sha256 = async (s: string) => {
    const msgBuffer = new TextEncoder().encode(s);
    const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    const hashHex = hashArray
      .map((b) => b.toString(16).padStart(2, '0'))
      .join('');
    return hashHex;
  };

  public async generateToken(
    username: string,
    password: string,
  ): Promise<string> {
    if (config.tgfs.users[username] === undefined) {
      throw new UserNotFound(username);
    }
    if (
      (await Auth.sha256(config.tgfs.users[username].password)) !== password
    ) {
      // the password sent in is sha256 hashed
      throw new IncorrectPassword(username);
    }

    return new Promise((resolve, reject) => {
      jwt.sign(
        {
          user: username,
          iat: Math.floor(Date.now() / 1000),
        },
        config.manager.jwt.secret,
        {
          issuer: 'tgfs-manager',
          audience: 'tgfs-manager',
          subject: username,
          expiresIn: config.manager.jwt.life,
          algorithm: config.manager.jwt.algorithm,
        } as jwt.SignOptions,
        (error, token) => {
          if (error) {
            this.logger.error(error);
            reject(new TechnicalError('token generation failed'));
          } else {
            this.context.user = username;
            this.logger.info(`jwt token issued`);
            resolve(token);
          }
        },
      );
    });
  }

  public async authenticate(token: string): Promise<JWTPayload> {
    return new Promise((resolve, reject) => {
      const payload = jwt.verify(
        config.manager.jwt.secret,
        token,
        (error, decoded: JWTPayload) => {
          if (error) {
            this.logger.error(error);
            reject(new JWTInvalid('verification failed'));
          } else {
            this.context.user = decoded.user;
            resolve(decoded);
          }
        },
      );
    });
  }
}
