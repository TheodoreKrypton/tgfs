import cliProgress from 'cli-progress';
import { Hash, createHash } from 'crypto';

import { Api, TelegramClient } from 'telegram';
import { IterDownloadFunction } from 'telegram/client/downloads';
import {
  EditMessageParams,
  IterMessagesParams,
  SendMessageParams,
} from 'telegram/client/messages';
import { FileLike } from 'telegram/define';

import fs from 'fs';

import { config } from 'src/config';
import { TechnicalError } from 'src/errors/base';

class MessageBroker {
  protected readonly privateChannelId = config.telegram.private_file_channel;

  constructor(
    protected readonly client: TelegramClient,
    protected buffer: Array<{
      ids: number[];
      resolve: (result: unknown) => void;
    }> = [],
    protected timeout: NodeJS.Timeout = null,
  ) {}

  async getMessagesByIds(ids: number[]) {
    return new Promise((resolve, reject) => {
      this.buffer.push({ ids, resolve });
      if (this.timeout) {
        clearTimeout(this.timeout);
      }
      this.timeout = setTimeout(async () => {
        let buffer = [];
        [buffer, this.buffer] = [[...this.buffer], []];
        const ids = [...new Set(buffer.map((item) => item.ids).flat())];
        const messages = await this.client.getMessages(this.privateChannelId, {
          ids,
        });
        const messageMap = new Map();
        messages.forEach((message) => {
          messageMap.set(message.id, message);
        });
        buffer.forEach((item) => {
          const result = item.ids.map((id: number) => messageMap.get(id));
          item.resolve(result);
        });
      }, 500);
    });
  }
}

export class MessageApi extends MessageBroker {
  constructor(protected readonly client: TelegramClient) {
    super(client);
  }

  protected async sendMessage(message: string | SendMessageParams) {
    if (typeof message === 'string') {
      message = { message };
    }
    return await this.client.sendMessage(this.privateChannelId, message);
  }

  protected async getMessages(params: Partial<IterMessagesParams>) {
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

  private async sha256(file: FileLike): Promise<Hash> {
    if (typeof file === 'string') {
      return new Promise((resolve) => {
        const rs = fs.createReadStream(file);
        const hash = createHash('sha256');
        rs.on('end', () => {
          hash.end();
          resolve(hash);
        });
        rs.pipe(hash);
      });
    } else if (file instanceof Buffer) {
      return createHash('sha256').update(file);
    } else {
      throw new TechnicalError('File format is illegal');
    }
  }

  protected async sendFile(file: FileLike) {
    const fileHash = (await this.sha256(file)).digest('hex');

    const existingFile = await this.getMessages({
      search: `#sha256IS${fileHash}`,
    });

    if (existingFile.length > 0) {
      return existingFile[0];
    }

    return await this.client.sendFile(this.privateChannelId, {
      file,
      caption: `#sha256IS${fileHash}`,
      workers: 16,
    });
  }

  protected async downloadFile(
    file: { name: string; messageId: number },
    withProgressBar?: boolean,
    options?: IterDownloadFunction,
  ) {
    const message = (await this.getMessagesByIds([file.messageId]))[0];

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
