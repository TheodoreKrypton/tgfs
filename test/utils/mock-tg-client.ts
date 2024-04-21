import { MockGramJSApi } from './mock-gramjs-api';
import { MockMessages } from './mock-messages';
import { MockTelegrafApi } from './mock-telegraf-api';

export const createMockClient = async () => {
  jest.resetModules();

  const mockMessages = new MockMessages();

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
        .mockImplementation(() => new MockGramJSApi(mockMessages)),
      loginAsAccount: jest.fn(),
      loginAsBot: jest.fn(),
    };
  });
  jest.mock('src/api/impl/telegraf', () => {
    return {
      TelegrafApi: jest
        .fn()
        .mockImplementation(() => new MockTelegrafApi(mockMessages)),
      createBot: jest.fn().mockImplementation(() => null),
    };
  });

  const { createClient } = require('src/api');

  return await createClient();
};
