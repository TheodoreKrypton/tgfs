import cliProgress from 'cli-progress';

import fs from 'fs';
import { Api, TelegramClient } from 'telegram';
import { IterDownloadFunction } from 'telegram/client/downloads';
import { FileLike } from 'telegram/define';

import { config } from '../../config';
import { TechnicalError } from '../../errors/base';
import { TGFSFileRef } from '../../model/directory';
import { TGFSFile } from '../../model/file';
import { MessageApi } from './message-api';

export class FileApi extends MessageApi {
  constructor(protected readonly client: TelegramClient) {
    super(client);
  }

  public async getFileInfo(fileRef: TGFSFileRef): Promise<TGFSFile> {
    const file = await this.getFileFromFileRef(fileRef);

    const versions = Object.values(file.versions);

    const fileMessages = await this.getMessagesByIds(
      versions.map((version) => version.messageId),
    );

    versions.forEach((version, i) => {
      const fileMessage = fileMessages[i];
      version.size = Number(fileMessage.document.size);
    });

    return file;
  }

  protected async downloadMediaByMessageId(
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

  public async downloadFileAtVersion(
    fileRef: TGFSFileRef,
    outputFile?: string | fs.WriteStream,
    versionId?: string,
  ): Promise<Buffer | null> {
    const tgfsFile = await this.getFileFromFileRef(fileRef);

    const version = versionId
      ? tgfsFile.getVersion(versionId)
      : tgfsFile.getLatest();

    const res = await this.downloadMediaByMessageId(
      { messageId: version.messageId, name: tgfsFile.name },
      true,
    );
    if (res instanceof Buffer) {
      if (outputFile) {
        if (outputFile instanceof fs.WriteStream) {
          outputFile.write(res);
        } else {
          fs.writeFile(outputFile, res, (err) => {
            if (err) {
              throw err;
            }
          });
        }
      }
      return res;
    } else {
      throw new TechnicalError(
        `Downloaded file is not a buffer. ${this.privateChannelId}/${version.messageId}`,
      );
    }
  }

  protected async sendFile(file: FileLike) {
    return await this.client.sendFile(this.privateChannelId, {
      file,
      workers: 16,
    });
  }

  public async getFileFromFileRef(fileRef: TGFSFileRef) {
    const message = (await this.getMessagesByIds([fileRef.getMessageId()]))[0];
    return TGFSFile.fromObject(JSON.parse(message.text));
  }
}
