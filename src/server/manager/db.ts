import { Task } from './model/task';

class Database {
  private downloadTasks: Map<string, Task>;
  private uploadTasks: Map<string, Task>;

  constructor() {
    this.downloadTasks = new Map();
    this.uploadTasks = new Map();
  }

  createTask(fileName: string, totalSize: number, type: 'download' | 'upload') {
    const task = new Task(fileName, totalSize, type);
    if (type === 'download') {
      this.downloadTasks[task.id] = task;
    } else {
      this.uploadTasks[task.id] = task;
    }

    return task;
  }

  getTasks() {
    return {
      download: this.downloadTasks,
      upload: this.uploadTasks,
    };
  }
}

export const db = new Database();
