import * as input from 'input';

import { Logger } from '../utils/logger';
import { login } from './login';

export const loginAsUser = login(async (client) => {
  await client.start({
    phoneNumber: async () => await input.text('number ?'),
    password: async () => await input.text('password?'),
    phoneCode: async () => await input.text('Code ?'),
    onError: (err) => Logger.error(err),
  });
});
