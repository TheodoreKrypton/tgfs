// a decorator limiting the number of times a function can be called in a second
// reqeusts exceeding limit will be awaiting for the next second
import { Queue } from './queue';
import { sleep } from './sleep';

const queue: Queue<{
  resolve: (value?: unknown) => void;
  reject: (reason?: unknown) => void;
  fn: Function;
  args: any[];
}> = new Queue();

const delay = 50;

(async () => {
  while (true) {
    await sleep(delay);
    if (queue.isEmpty()) {
      continue;
    }

    const { resolve, reject, fn, args } = queue.dequeue();

    try {
      const res = await fn(...args);
      resolve(res);
    } catch (err) {
      reject(err);
    }
  }
})();

export function flowControl() {
  return function (
    _target: any,
    _propertyKey: string,
    descriptor: PropertyDescriptor,
  ) {
    const originalMethod = descriptor.value!;

    descriptor.value = function (...args: any[]) {
      return new Promise((resolve, reject) => {
        if (process.env['NODE_ENV'] === 'test') {
          originalMethod
            .bind(this)(...args)
            .then((res) => {
              resolve(res);
            })
            .catch((err) => {
              reject(err);
            });
        } else {
          queue.enqueue({
            resolve,
            reject,
            fn: originalMethod.bind(this),
            args,
          });
        }
      });
    };

    return descriptor;
  };
}
