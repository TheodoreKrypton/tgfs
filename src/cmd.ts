import { loginAsBot } from './auth';
import { Executor } from './commands/executor';
import { parse } from './commands/parser';
import { BusinessError } from './errors/base';

(async () => {
  try {
    const client = await loginAsBot();

    await client.init();

    const executor = new Executor(client);

    const argv = parse();
    await executor.execute(argv);
  } catch (err) {
    if (err instanceof BusinessError) {
      console.log(err.message);
    } else {
      console.error(err);
    }
  } finally {
    process.exit(0);
  }
})();
