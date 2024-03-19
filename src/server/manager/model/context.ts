export type Context = {
  id: string;
  user?: string;
};

export class WithContext {
  constructor(protected readonly context: Context) {}
}
