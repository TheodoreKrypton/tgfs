# tgfs

Use telegram as file storage

[![Test](https://github.com/TheodoreKrypton/tgfs/actions/workflows/test.yml/badge.svg)](https://github.com/TheodoreKrypton/tgfs/actions/workflows/test.yml) [![codecov](https://codecov.io/gh/TheodoreKrypton/tgfs/branch/master/graph/badge.svg?token=CM6TF4C9B9)](https://codecov.io/gh/TheodoreKrypton/tgfs)

Tested on Windows, Ubuntu, MacOS

## Installation

```bash
$ yarn install && yarn build
$ alias tgfs="yarn cmd"
```

## Step by Step Guide to Set up Environment Variables

### Create a Telegram app

1. Go to [Here](https://my.telegram.org/apps), login with your phone number and create a Telegram app.

### Set up `api_id` and `api_hash`

1. Duplicate the .env.example file and name it .env.local
2. Copy the `api_id` and `api_hash` from the Telegram app page to the .env.local file (`TELEGRAM_API_ID` and `TELEGRAM_API_HASH` respectively)

### Set up the channel to store files

1. Create a new Telegram private channel (New Channel in the menu on the left)
2. There should be a message like "Channel created". Right click the message and copy the post link.
3. The format of the link should be like `https://t.me/c/1234567/1`, where `1234567` is the channel id. Copy the channel id to the .env.local file (`TELEGRAM_PRIVATE_FILE_CHANNEL`)

### Create a Telegram bot

1. Go to [BotFather](https://t.me/botfather), create a new bot and copy the token to the .env.local file (`TELEGRAM_BOT_TOKEN`)
2. Add the bot to the channel as an administrator

### Choose where to store the session file

1. You can do this by editing the `TELEGRAM_SESSION_FILE` variable in the .env.local file. The default value is `~/.tgfs/account.session`

## usage

- ls

  ```bash
  $ tgfs ls /
  ```

- mkdir

  ```bash
  $ tgfs mkdir /documents
  ```

- cp

  ```bash
  $ tgfs cp ~/some-file /
  ```

- rm

  ```bash
  $ tgfs rm /some-file
  ```
