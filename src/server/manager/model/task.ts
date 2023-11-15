import { v4 as uuid } from 'uuid';

export class Task {
  id: string;
  fileName: string;
  totalSize: number;
  completedSize: number;
  status: 'queuing' | 'in-progress' | 'completed';
  type: 'download' | 'upload';
  beginTime: number;

  constructor(
    fileName: string,
    totalSize: number,
    type: 'download' | 'upload',
  ) {
    this.id = uuid();
    this.fileName = fileName;
    this.totalSize = totalSize;
    this.status = 'queuing';
    this.type = type;
    this.beginTime = Date.now();
  }

  begin() {
    this.status = 'in-progress';
  }

  finish() {
    this.status = 'completed';
  }

  reportProgress(size: number) {
    this.completedSize = size;
  }
}
