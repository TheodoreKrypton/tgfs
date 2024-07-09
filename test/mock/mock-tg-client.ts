import { Client } from 'src/api';
import { FakeGramJSApi } from 'src/api/impl/fake/gramjs';
import { Messages } from 'src/api/impl/fake/messages';
import { FakeTelegraf } from 'src/api/impl/fake/telegraf';

export const createMockClient = async (): Promise<Client> => {
  jest.resetModules();

  const mockMessages = new Messages();

  jest.mock('src/config', () => {
    return {
      config: {
        telegram: {
          private_file_channel: '114514',
        },
        tgfs: {
          download: {
            chunk_size_kb: 1024,
          },
        },
      },
    };
  });
  jest.mock('src/api/impl/gramjs', () => {
    return {
      GramJSApi: jest
        .fn()
        .mockImplementation(() => new FakeGramJSApi(mockMessages)),
      loginAsAccount: jest.fn(),
      loginAsBot: jest.fn(),
    };
  });
  jest.mock('src/api/impl/telegraf', () => {
    return {
      TelegrafApi: jest.fn().mockImplementation(() => new FakeTelegraf()),
      createBot: jest.fn().mockImplementation(() => null),
    };
  });

  const { createClient } = require('src/api');

  return await createClient();
};
