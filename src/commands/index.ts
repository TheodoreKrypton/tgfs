import { hideBin } from 'yargs/helpers';
import yargs from 'yargs/yargs';

// Parse arguments
const argv: any = yargs(hideBin(process.argv))
  .command('get', 'get the latest message', (yargs) => {
    return yargs.option('chatId', {
      describe: 'ID of the chat to retrieve messages from',
      demandOption: true,
      type: 'string',
    });
  })
  .command('send', 'send a message', (yargs) => {
    return yargs
      .option('chatId', {
        describe: 'ID of the chat to send a message to',
        demandOption: true,
        type: 'string',
      })
      .option('message', {
        describe: 'The message to send',
        demandOption: true,
        type: 'string',
      });
  })
  .demandCommand(1, 'You need at least one command before moving on')
  .help().argv;

// Use argv.command, argv.chatId, and argv.message as needed in your program
if (argv._[0] === 'get') {
  // Implement the functionality to get messages using the given chatId
  console.log(`Getting messages for chat ID: ${argv.chatId}`);
} else if (argv._[0] === 'send') {
  // Implement the functionality to send a message to the given chatId
  console.log(
    `Sending message to chat ID: ${argv.chatId}, message: ${argv.message}`,
  );
}
