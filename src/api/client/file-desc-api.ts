import { TGFSFileRef } from 'src/model/directory';
import { TGFSFile } from 'src/model/file';

import { MessageApi } from './message-api';
import { GeneralFileMessage } from './message-api/types';

export class FileDescApi extends MessageApi {
  public async createFileDesc(file: GeneralFileMessage): Promise<number> {
    const tgfsFile = new TGFSFile(file.name);

    if ('empty' in file) {
      tgfsFile.addEmptyVersion();
    } else {
      const id = await this.sendFile(file);
      tgfsFile.addVersionFromFileMessageId(id);
    }

    return await this.sendText(JSON.stringify(tgfsFile.toObject()));
  }

  public async getFileDesc(
    fileRef: TGFSFileRef,
    withVersionInfo: boolean = true,
  ): Promise<TGFSFile> {
    const message = (await this.getMessages([fileRef.getMessageId()]))[0];

    const fileDesc = TGFSFile.fromObject(JSON.parse(message.text));

    if (withVersionInfo) {
      const versions = Object.values(fileDesc.versions);

      const nonEmptyVersions = versions.filter(
        (version) => version.messageId > 0,
      ); // may contain empty versions

      const fileMessages = await this.getMessages(
        nonEmptyVersions.map((version) => version.messageId),
      );

      nonEmptyVersions.forEach((version, i) => {
        const fileMessage = fileMessages[i];
        if (fileMessage) {
          version.size = Number(fileMessage.document.size);
        } else {
          version.setInvalid();
        }
      });
    }

    return fileDesc;
  }

  public async updateFileDesc(fr: TGFSFileRef, fd: TGFSFile): Promise<number> {
    return await this.editMessageText(
      fr.getMessageId(),
      JSON.stringify(fd.toObject()),
    );
  }
}
