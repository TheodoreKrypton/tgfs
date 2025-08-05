"use client";

class CatchableError extends Error {
  constructor(message: string) {
    super(message);
  }
}

const errors = { CatchableError };

export default errors;
