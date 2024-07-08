import { FileDescAPIResponse } from 'src/api/client/model';
import { TGFSFileRef } from 'src/model/directory';
import { TGFSFile } from 'src/model/file';

import { GeneralFileMessage, isFileMessageEmpty } from './model';
import { FileRepository } from './repository/impl/file';
import { IFDRepository } from './repository/interface';

export class FileDescApi {
  constructor(
    private readonly fdRepo: IFDRepository,
    private readonly fileRepo: FileRepository,
  ) {}

  public async createFileDesc(
    fileMsg: GeneralFileMessage,
  ): Promise<FileDescAPIResponse> {
    const fd = new TGFSFile(fileMsg.name);

    if ('empty' in fileMsg) {
      fd.addEmptyVersion();
    } else {
      const sentFileMsg = await this.fileRepo.save(fileMsg);
      fd.addVersionFromSentFileMessage(sentFileMsg);
    }

    return await this.fdRepo.save(fd);
  }

  public async getFileDesc(fr: TGFSFileRef): Promise<TGFSFile> {
    return await this.fdRepo.get(fr);
  }

  public async addFileVersion(
    fr: TGFSFileRef,
    fileMsg: GeneralFileMessage,
  ): Promise<FileDescAPIResponse> {
    const fd = await this.getFileDesc(fr);

    if (isFileMessageEmpty(fileMsg)) {
      fd.addEmptyVersion();
    } else {
      const sentFileMsg = await this.fileRepo.save(fileMsg);
      fd.addVersionFromSentFileMessage(sentFileMsg);
    }
    await this.fdRepo.save(fd, fr.getMessageId());
    return { messageId: fr.getMessageId(), fd };
  }

  public async updateFileVersion(
    fr: TGFSFileRef,
    fileMsg: GeneralFileMessage,
    versionId: string,
  ): Promise<FileDescAPIResponse> {
    const fd = await this.getFileDesc(fr);
    if (isFileMessageEmpty(fileMsg)) {
      const fv = fd.getVersion(versionId);
      fv.setInvalid();
      fd.updateVersion(fv);
    } else {
      const sentFileMsg = await this.fileRepo.save(fileMsg);
      const fv = fd.getVersion(versionId);
      fv.messageId = sentFileMsg.messageId;
      fv.size = sentFileMsg.size.toJSNumber();
      fd.updateVersion(fv);
    }
    await this.fdRepo.save(fd, fr.getMessageId());
    return { messageId: fr.getMessageId(), fd };
  }

  public async deleteFileVersion(
    fr: TGFSFileRef,
    versionId: string,
  ): Promise<FileDescAPIResponse> {
    const fd = await this.getFileDesc(fr);
    fd.deleteVersion(versionId);
    await this.fdRepo.save(fd, fr.getMessageId());
    return { messageId: fr.getMessageId(), fd };
  }
}
