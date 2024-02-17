import { ErrorCodes } from './error-codes';

export class TechnicalError extends Error {
  constructor(
    public readonly message: string,
    public readonly cause?: any,
  ) {
    super(message);
  }
}

export class BusinessError extends TechnicalError {
  constructor(
    public readonly message: string,
    public readonly code: ErrorCodes,
    public readonly cause?: any,
  ) {
    super(message, cause);
  }
}

export class AggregatedError extends Error {
  constructor(public readonly errors: Error[]) {
    super(errors.map((e) => e.message).join('\n'));
  }
}
