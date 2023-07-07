import { loginAsBot } from './auth/as-bot';

(async () => {
  const client = await loginAsBot();
  await client.init();

  // console.log(
  //   await client.createDirectoryUnder('test-create', client.metadata.dir),
  // );

  // await client.newFileUnder(
  //   'ChenYonghua.pdf',
  //   client.metadata.dir,
  //   '/mnt/c/Users/theod/Desktop/ChenYonghua-05052023.pdf',
  // );

})();
