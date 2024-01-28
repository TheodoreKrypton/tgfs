import { Api } from 'telegram';
import { TelegramClient } from 'telegram';
import { IterDownloadFunction } from 'telegram/client/downloads';
import { SendFileInterface } from 'telegram/client/uploads';
import { EntityLike } from 'telegram/define';

import { Telegram } from 'telegraf';

import { createClient } from 'src/api';
import { Config } from 'src/config';

import { MockMessages } from './mock-messages';

let mockMessages = null;

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
                const file = mockMessages.getFile(
                  Number((fileLoc as Api.InputDocumentFileLocation).id),
                );
                let done = false;
                return {
                  [Symbol.asyncIterator]() {
                    return {
                      next() {
                        const res = Promise.resolve({
                          value: file.buffer,
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
                (entity: EntityLike, sendFileParams: SendFileInterface) => {
                  let id = 0;
                  if (sendFileParams instanceof Api.InputFileBig) {
                    id = mockMessages.sendMessage({
                      file: {
                        id: sendFileParams.id,
                        parts: sendFileParams.parts,
                        name: sendFileParams.name,
                      },
                    });
                  } else {
                    id = mockMessages.sendMessage({
                      file: sendFileParams.file,
                    });
                  }

                  return { id };
                },
              ),

            invoke: jest.fn().mockImplementation((request: any) => {
              if (request instanceof Api.upload.SaveBigFilePart) {
                return true;
              }
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
        sendDocument: jest
          .fn()
          .mockImplementation(
            (
              chatId: string,
              document: { source: string | Buffer; filename: string },
            ) => {
              const { source } = document;

              let messageId = 0;
              if (typeof source === 'string') {
                messageId = mockMessages.sendMessage({
                  file: Buffer.from(source),
                });
              } else {
                messageId = mockMessages.sendMessage({
                  file: source,
                });
              }

              return { message_id: messageId };
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
            mockMessages.editMessage(messageId, {
              file: media.media.source,
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
