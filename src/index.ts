import { loginAsBot } from './auth/as-bot';

(async () => {
  const client = await loginAsBot();
  await client.init();

  // console.log(
  //   await client.createDirectoryUnder('test-create', client.metadata.dir),
  // );

  // await client.newFileUnder(
  //   'test-file2',
  //   client.metadata.dir,
  //   '~/test-file2',
  // );

  console.log(
    String(
      await client.downloadFile(
        await client.getFileAtVersion(client.metadata.dir.files[1]),
      ),
    ),
  );
})();
