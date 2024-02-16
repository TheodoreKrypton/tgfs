import { Api, TelegramClient } from 'telegram';
import { IterDownloadFunction } from 'telegram/client/downloads';
import { EntityLike } from 'telegram/define';

import { Telegram } from 'telegraf';

import { createClient } from 'src/api';
import { generateFileId } from 'src/api/utils';
import { Config } from 'src/config';

import { MockMessages } from './mock-messages';

let mockMessages: MockMessages = null;

jest.mock('src/config', () => {
  return {
    ...jest.requireActual('src/config'),
    config: {
      telegram: {
        private_file_channel: 'mock-private-file-channel',
      },
      tgfs: {
        download: {
          chunk_size_kb: 1024,
        },
      },
    } as Partial<Config>,
  };
});

jest.mock('src/api/impl/gramjs', () => {
  return {
    ...jest.requireActual('src/api/impl/gramjs'),
    loginAsAccount: jest.fn().mockImplementation(async () => {
      return new TelegramClient('mock-session', 0, 'mock-api-hash', {});
    }),
    loginAsBot: jest.fn().mockImplementation(async () => {
      return new TelegramClient('mock-session', 0, 'mock-api-hash', {});
    }),
  };
});

jest.mock('src/api/impl/telegraf', () => {
  return {
    ...jest.requireActual('src/api/impl/telegraf'),
    createBot: jest.fn().mockImplementation(() => {
      return new Telegram('mock-token');
    }),
  };
});

jest.mock('telegram', () => {
  return {
    ...jest.requireActual('telegram'),
    TelegramClient: jest
      .fn()
      .mockImplementation(
        (session: string, apiId: number, apiHash: string, options: any) => {
          return {
            getMessages: jest
              .fn()
              .mockImplementation((channelId: string, options: any) => {
                const { filter, ids, search } = options;
                if (filter instanceof Api.InputMessagesFilterPinned) {
                  return mockMessages.pinnedMessageId
                    ? [mockMessages.getMessage(mockMessages.pinnedMessageId)]
                    : [];
                }
                if (search) {
                  return mockMessages.search(search);
                }
                return ids.map((id: number) => mockMessages.getMessage(id));
              }),
            iterDownload: jest
              .fn()
              .mockImplementation((iterFileParams: IterDownloadFunction) => {
                const { file: fileLoc } = iterFileParams;
                const fileParts = mockMessages.getFile(
                  (fileLoc as Api.InputDocumentFileLocation).id,
                );
                mockMessages;
                let done = false;
                let i = 0;
                return {
                  [Symbol.asyncIterator]() {
                    return {
                      next() {
                        const res = Promise.resolve({
                          value: fileParts[i++],
                          done,
                        });
                        done = !done;
                        return res;
                      },
                      return() {
                        return { done: true };
                      },
                    };
                  },
                };
              }),

            sendFile: jest
              .fn()
              .mockImplementation(
                (entity: EntityLike, { file: { id: fileId } }) => {
                  const id = mockMessages.sendMessage({
                    file: fileId,
                  });
                  return { id };
                },
              ),

            invoke: jest.fn().mockImplementation((req: any) => {
              return mockMessages.saveFilePart(
                req.fileId,
                req.filePart,
                req.bytes,
              );
            }),
          };
        },
      ),
  };
});
jest.mock('telegraf', () => {
  return {
    Telegram: jest.fn().mockImplementation((botToken: string) => {
      return {
        sendMessage: jest
          .fn()
          .mockImplementation((chatId: string, text: string) => {
            const messageId = mockMessages.sendMessage({ message: text });
            return { message_id: messageId };
          }),
        editMessageText: jest
          .fn()
          .mockImplementation(
            (
              chatId: string,
              messageId: number,
              inlineMessageId,
              text: string,
            ) => {
              mockMessages.editMessage(messageId, { message: text });
            },
          ),
        editMessageMedia: jest.fn().mockImplementation(
          (
            chatId: string,
            messageId: number,
            inlineMessageId: undefined | string,
            media: {
              type: 'document';
              media: {
                source: Buffer;
              };
            },
          ) => {
            const fileId = generateFileId();
            mockMessages.saveFilePart(fileId, 0, media.media.source);
            mockMessages.editMessage(messageId, {
              file: fileId,
            });
          },
        ),
        pinChatMessage: jest
          .fn()
          .mockImplementation((chatId: string, messageId: number) => {
            mockMessages.pinnedMessageId = messageId;
          }),
      };
    }),
  };
});

export const createMockClient = async () => {
  mockMessages = new MockMessages();
  const client = await createClient();
  return client;
};
