import { Logger } from 'src/utils/logger';

export function retry(
  retries: number = 3,
  backoff: number = 500,
): MethodDecorator {
  return function (
    _target: Object,
    propertyKey: string | symbol,
    descriptor: PropertyDescriptor,
  ) {
    const originalMethod = descriptor.value;
    descriptor.value = async function (...args: any[]) {
      for (let i = 0; i <= retries; i++) {
        try {
          const result = await originalMethod.apply(this, args);
          return result;
        } catch (error) {
          if (i === retries) throw error;
          const waitTime = Math.pow(2, i) * backoff;
          Logger.error(
            `Method ${String(propertyKey)}: Attempt ${i + 1} failed. Retrying in ${waitTime}ms...`,
          );
          await new Promise((resolve) => setTimeout(resolve, waitTime));
        }
      }
    };
    return descriptor;
  };
}
