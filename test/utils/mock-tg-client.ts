import { Api, TelegramClient } from 'telegram';
import { IterDownloadFunction } from 'telegram/client/downloads';
import { EditMessageParams, SendMessageParams } from 'telegram/client/messages';
import { SendFileInterface } from 'telegram/client/uploads';
import { EntityLike } from 'telegram/define';

import { Client } from 'src/api';

import { MockMessages } from './mock-messages';

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
          const mockMessages = new MockMessages();
          return {
            getMessages: jest
              .fn()
              .mockImplementation((channelId: string, options: any) => {
                let { filter, ids } = options;
                if (filter instanceof Api.InputMessagesFilterPinned) {
                  return mockMessages.pinnedMessageId
                    ? [mockMessages.getMessage(mockMessages.pinnedMessageId)]
                    : [];
                }
                return ids.map((id: number) => mockMessages.getMessage(id));
              }),
            sendMessage: jest
              .fn()
              .mockImplementation(
                (entity: EntityLike, sendMessageParams?: SendMessageParams) => {
                  const messageId = mockMessages.sendMessage(sendMessageParams);
                  return { id: messageId };
                },
              ),
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
            pinMessage: jest
              .fn()
              .mockImplementation((entity: EntityLike, id: number) => {
                mockMessages.pinnedMessageId = id;
              }),
            editMessage: jest
              .fn()
              .mockImplementation(
                (entity: EntityLike, editMessageParams: EditMessageParams) => {
                  mockMessages.editMessage(
                    editMessageParams.message as number,
                    editMessageParams,
                  );
                },
              ),

            sendFile: jest
              .fn()
              .mockImplementation(
                (entity: EntityLike, sendFileParams: SendFileInterface) => {
                  const id = mockMessages.sendMessage({
                    file: sendFileParams.file,
                  });
                  return { id };
                },
              ),
          };
        },
      ),
  };
});

export const createClient = async () => {
  const client = new Client(
    new TelegramClient('mock-session', 0, 'mock-api-hash', {}),
  );
  await client.init();
  return client;
};
