import { Api, TelegramClient } from 'telegram';
import { DownloadMediaInterface } from 'telegram/client/downloads';
import { EditMessageParams, SendMessageParams } from 'telegram/client/messages';
import { SendFileInterface } from 'telegram/client/uploads';
import { EntityLike } from 'telegram/define';

import { Client } from 'src/api';

import { MockMessages } from './mock-messages';

jest.mock('telegram', () => {
  return {
    Api: {
      InputMessagesFilterPinned: jest.fn(),
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
            downloadMedia: jest
              .fn()
              .mockImplementation(
                (
                  messageOrMedia: { id: number },
                  downloadParams?: DownloadMediaInterface,
                ) => {
                  return mockMessages.getMessage(messageOrMedia.id).file;
                },
              ),
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
    'mock-private-channel-id',
    'mock-public-channel-id',
  );
  await client.init();
  return client;
};
