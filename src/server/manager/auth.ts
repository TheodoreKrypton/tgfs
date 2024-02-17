import jwt from 'json-web-token';

import { config } from 'src/config';
import { IncorrectPassword, JWTInvalid, UserNotFound } from 'src/errors';

const sha256 = async (s: string) => {
  const msgBuffer = new TextEncoder().encode(s);
  const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  const hashHex = hashArray
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');
  return hashHex;
};

type JWTPayload = {
  username: string;
  exp: number;
};

export const generateToken = async (username: string, password: string) => {
  if (config.tgfs.users[username] === undefined) {
    throw new UserNotFound(username);
  }
  if ((await sha256(config.tgfs.users[username].password)) !== password) {
    // the password sent in is sha256 hashed
    throw new IncorrectPassword(username);
  }
  return jwt.encode;
};

export const verifyToken = (token: string): Promise<JWTPayload> => {
  return new Promise((resolve, reject) => {
    const payload = jwt.decode(
      config.manager.jwt.secret,
      token,
      (error, payload) => {
        if (error) {
          reject(new JWTInvalid());
        }
      },
    );
    if (payload.exp < Date.now()) {
      reject(new JWTInvalid());
    }
    resolve(payload as JWTPayload);
  });
};
