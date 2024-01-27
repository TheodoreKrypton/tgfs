import { Api, TelegramClient } from 'telegram';
import { IterDownloadFunction } from 'telegram/client/downloads';
import { SendFileInterface } from 'telegram/client/uploads';
import { EntityLike } from 'telegram/define';

import { Telegram } from 'telegraf';

import { Client } from 'src/api';

import { MockMessages } from './mock-messages';

let mockMessages = null;

jest.mock('src/config', () => {
  return {
    config: {
      telegram: {
        private_file_channel: 'mock-private-file-channel',
      },
      tgfs: {
        download: {
          chunksize: 1024,
          progress: false,
        },
      },
    },
  };
});

jest.mock('telegram', () => {
  return {
    Api: {
      InputMessagesFilterPinned: jest.fn(),
      InputDocumentFileLocation: jest.fn().mockImplementation((file) => {
        return file;
      }),
    },
    TelegramClient: jest
      .fn()
      .mockImplementation(
        (session: string, apiId: number, apiHash: string, options: any) => {
          return {
            getMessages: jest
              .fn()
              .mockImplementation((channelId: string, options: any) => {
                let { filter, ids, search } = options;
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
                  const id = mockMessages.sendMessage({
                    file: sendFileParams.file,
                    message: sendFileParams.caption as string,
                  });
                  return { id };
                },
              ),
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

export const createClient = async () => {
  mockMessages = new MockMessages();

  const client = new Client(
    new TelegramClient('mock-session', 1, 'mock-api-hash', {}),
    new Telegram('mock-bot-token'),
  );

  await client.init();

  return client;
};
