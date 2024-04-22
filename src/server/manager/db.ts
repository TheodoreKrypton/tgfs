import { Task } from './model/task';

class Database {
  private downloadTasks: Map<string, Task>;
  private uploadTasks: Map<string, Task>;

  constructor() {
    this.downloadTasks = new Map();
    this.uploadTasks = new Map();
  }

  private createTask(
    fileName: string,
    totalSize: bigInt.BigInteger,
    type: 'download' | 'upload',
  ): Task {
    const task = new Task(fileName, totalSize, type);
    if (type === 'download') {
      this.downloadTasks[task.id] = task;
    } else {
      this.uploadTasks[task.id] = task;
    }

    return task;
  }

  createUploadTask(fileName: string, totalSize: bigInt.BigInteger): Task {
    return this.createTask(fileName, totalSize, 'upload');
  }

  createDownloadTask(fileName: string, totalSize: bigInt.BigInteger): Task {
    return this.createTask(fileName, totalSize, 'download');
  }

  getTasks() {
    return {
      download: this.downloadTasks,
      upload: this.uploadTasks,
    };
  }
}

export const manager = new Database();
