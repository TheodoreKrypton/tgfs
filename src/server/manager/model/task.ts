import { v4 as uuid } from 'uuid';

export class Task {
  id: string;
  fileName: string;
  totalSize: bigInt.BigInteger;
  completedSize: bigInt.BigInteger;
  status: 'queuing' | 'in-progress' | 'completed' | 'failed';
  type: 'download' | 'upload';
  beginTime: number;
  errors: Error[] = [];

  constructor(
    fileName: string,
    totalSize: bigInt.BigInteger,
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

  complete() {
    this.status = 'completed';
  }

  setErrors(errors: Error[]) {
    this.errors = errors;
  }

  reportProgress(size: bigInt.BigInteger) {
    this.completedSize = size;
  }
}
