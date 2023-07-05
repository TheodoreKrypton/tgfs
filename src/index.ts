import { loginAsBot } from './auth/as-bot';

(async () => {
  const client = await loginAsBot();
  await client.init();

  console.log(
    await client.createDirectoryUnder('test-create', client.metadata.dir),
  );
})();
