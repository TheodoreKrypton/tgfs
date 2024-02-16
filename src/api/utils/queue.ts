class QueueItem<T> {
  value: T;
  next: QueueItem<T>;
  prev: QueueItem<T>;

  constructor(value: T) {
    this.value = value;
    this.next = null;
    this.prev = null;
  }
}

export class Queue<T> {
  private head: QueueItem<T>;
  private tail: QueueItem<T>;
  private _size: number;

  constructor() {
    this.head = null;
    this.tail = null;
    this._size = 0;
  }

  enqueue(value: T): void {
    const node = new QueueItem(value);
    if (!this.head) {
      this.head = node;
      this.tail = node;
    } else {
      if (this.tail) {
        this.tail.next = node;
        node.prev = this.tail;
      }
      this.tail = node;
    }
    this._size++;
  }

  enqueueFront(value: T): void {
    const node = new QueueItem(value);
    if (!this.head) {
      this.head = node;
      this.tail = node;
    } else {
      if (this.head) {
        this.head.prev = node;
        node.next = this.head;
      }
      this.head = node;
    }
    this._size++;
  }

  dequeue(): T {
    if (!this.head) {
      return null;
    }
    const value = this.head.value;
    this.head = this.head.next;
    if (this.head) {
      this.head.prev = null;
    } else {
      this.tail = null;
    }
    this._size--;
    return value;
  }

  peek(): T {
    return this.head ? this.head.value : null;
  }

  size(): number {
    return this._size;
  }

  isEmpty(): boolean {
    return this.size() === 0;
  }
}
