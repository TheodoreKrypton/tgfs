# tgfs

Use telegram as file storage, with a command line tool and WebDAV server.

[![Test](https://github.com/TheodoreKrypton/tgfs/actions/workflows/test.yml/badge.svg)](https://github.com/TheodoreKrypton/tgfs/actions/workflows/test.yml) [![codecov](https://codecov.io/gh/TheodoreKrypton/tgfs/branch/master/graph/badge.svg?token=CM6TF4C9B9)](https://codecov.io/gh/TheodoreKrypton/tgfs)

Tested on Windows, Ubuntu, MacOS

## Installation

### Through Git

```bash
$ yarn install && yarn build
$ alias tgfs="yarn start:prod"
```

## Step by Step Guide to Set up config

### First step

1. Duplicate the `example-config.yaml` file and name it `config.yaml`
2. Go to [Here](https://my.telegram.org/apps), login with your phone number and create a Telegram app.
3. Copy the `api_id` and `api_hash` from the Telegram app page (step 2) to the config file (`telegram -> api_id / api_hash`)

### Set up the channel to store files

1. Create a new Telegram private channel (New Channel in the menu on the left)
2. There should be a message like "Channel created". Right click the message and copy the post link.
3. The format of the link should be like `https://t.me/c/1234567/1`, where `1234567` is the channel id. Copy the channel id to the config file (`telegram -> private_file_channel`)

### Create a Telegram bot (Optional, if you don't want to use your own account)

1. Go to [BotFather](https://t.me/botfather), create a new bot and copy the token to the config file (`telegram -> bot_token`)
2. Add the bot to the channel as an administrator

### Choose where to store the session file (Optional)

1. You can do this by editing the `telegram -> session_file` variable in the config file. The default path is `~/.tgfs/account.session`

## cmd usage

- ls

  ```bash
  $ tgfs cmd ls /
  ```

- mkdir

  ```bash
  $ tgfs cmd mkdir /documents
  ```

  ```bash
  $ tgfs cmd mkdir -p /documents/pictures
  ```

- cp

  ```bash
  $ tgfs cmd cp ~/some-file /
  ```

- rm

  ```bash
  $ tgfs cmd rm /some-file
  ```

  ```bash
  $ tgfs cmd rm -r /some-folder
  ```

## Use it as a WebDAV server

```
$ tgfs -w [-h HOST] [-p PORT]
```

or

```
$ tgfs --webdav [-h HOST] [-p PORT]
```

Tested WebDAV Clients:

- [Cyberduck](https://cyberduck.io/)
- [File Stash](https://www.filestash.app/)
