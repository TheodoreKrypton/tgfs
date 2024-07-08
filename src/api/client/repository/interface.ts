import { FileDescAPIResponse } from 'src/api/client/model';
import { TGFSFileRef } from 'src/model/directory';
import { TGFSFile } from 'src/model/file';
import { TGFSMetadata } from 'src/model/metadata';

export interface IFDRepository {
  save(fd: TGFSFile, messageId?: number): Promise<FileDescAPIResponse>;
  get(fr: TGFSFileRef): Promise<TGFSFile>;
}

export interface IMetaDataRepository {
  save(metaData: TGFSMetadata): Promise<number>;
  get(): Promise<TGFSMetadata>;
}
