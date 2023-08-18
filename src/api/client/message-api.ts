import cliProgress from 'cli-progress';

import { Api, TelegramClient } from 'telegram';
import { IterDownloadFunction } from 'telegram/client/downloads';
import {
  EditMessageParams,
  IterMessagesParams,
  SendMessageParams,
} from 'telegram/client/messages';
import { FileLike, MessageLike } from 'telegram/define';

import { config } from 'src/config';

export class MessageApi {
  private readonly privateChannelId = config.telegram.private_file_channel;

  constructor(protected readonly client: TelegramClient) {}

  protected async sendMessage(message: string | SendMessageParams) {
    if (typeof message === 'string') {
      message = { message };
    }
    return await this.client.sendMessage(this.privateChannelId, message);
  }

  protected async getMessages(params: number[] | Partial<IterMessagesParams>) {
    if (Array.isArray(params)) {
      params = { ids: params };
    }
    return await this.client.getMessages(this.privateChannelId, params);
  }

  protected async editMessage(
    messageId: number,
    editMessageParams: Partial<EditMessageParams>,
  ) {
    return await this.client.editMessage(this.privateChannelId, {
      message: messageId,
      ...editMessageParams,
    });
  }

  protected async pinMessage(messageId: number) {
    return await this.client.pinMessage(this.privateChannelId, messageId);
  }

  protected async sendFile(file: FileLike) {
    return await this.client.sendFile(this.privateChannelId, {
      file,
      workers: 16,
    });
  }

  protected async downloadFile(
    file: { name: string; messageId: number },
    withProgressBar?: boolean,
    options?: IterDownloadFunction,
  ) {
    const message = (await this.getMessages([file.messageId]))[0];

    const fileSize = Number(message.document.size);
    const chunkSize = config.tgfs.download.chunksize * 1024;

    let pgBar: cliProgress.SingleBar;
    if (withProgressBar) {
      pgBar = new cliProgress.SingleBar({
        format: `${file.name} [{bar}] {percentage}%`,
      });
      pgBar.start(fileSize, 0);
    }

    const buffer = Buffer.alloc(fileSize);
    let i = 0;
    for await (const chunk of this.client.iterDownload({
      file: new Api.InputDocumentFileLocation({
        id: message.document.id,
        accessHash: message.document.accessHash,
        fileReference: message.document.fileReference,
        thumbSize: '',
      }),
      requestSize: chunkSize,
    })) {
      chunk.copy(buffer, i * chunkSize, 0, Number(chunk.length));
      i += 1;

      if (withProgressBar) {
        pgBar.update(i * chunkSize);
      }
    }
    return buffer;
  }
}
