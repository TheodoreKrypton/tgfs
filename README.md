<p align="center">
  <img src="https://raw.githubusercontent.com/TheodoreKrypton/tgfs/master/tgfs.png" alt="logo" width="100"/>
</p>

# tgfs

Telegram becomes a WebDAV server.

Refer to the [wiki page](https://github.com/TheodoreKrypton/tgfs/wiki/TGFS-Wiki) for technical detail.

## Installation

### Through Docker

You must prepare a directory (defaulted to .tgfs) to store the app data, and place a `config.yaml` file in it.

Refer to the [Set up config file](#set-up-config-file) section for creating the `config.yaml` file.

```bash
docker run -d --name tgfs \
  -v .tgfs:/home/tgfs/.tgfs \  # Volume to store app data. config.yaml is in this directory.
  -p 1900:1900 \
  wheatcarrier/tgfs
```

Tested WebDAV Clients:

- [Cyberduck](https://cyberduck.io/)

## Set up config file

> **WARNING:** For feature development purpose, any configuration is **unstable** at the current stage. You may need to reconfigure following any update.

#### Preparation

1. Duplicate the `example-config.yaml` file and name it `config.yaml`, place it in the `.tgfs` directory (or the directory you specified in the Docker command).

#### Set up account details ([why do I need this?](#FAQ))

1. Go to [Here](https://my.telegram.org/apps), login with your phone number and create a Telegram app.
2. Copy the `api_id` and `api_hash` from the Telegram app page (step 2) to the config file (`telegram -> account -> api_id / api_hash`)

#### Set up the channel to store files

1. Create a new Telegram private channel (New Channel in the menu on the left)
2. There should be a message like "Channel created". Right click the message and copy the post link.
3. The format of the link should be like `https://t.me/c/1234567/1`, where `1234567` is the channel id. Copy the channel id to the config file (`telegram -> private_file_channel`)

#### Set up a Telegram bot ([why do I need this?](#FAQ))

1. Go to [BotFather](https://telegram.me/BotFather), send `/newbot`, and follow the steps to create a bot.
2. Paste the bot token given by BotFater to the config file (`telegram -> bot -> tokens`)
3. Go to your file channel (created in the previous step), add your bot to subscriber, and promote it to admin, with permission to send/edit/delete messages.

#### [Optional] Add additional bot accounts

1. Follow the same step as above to create other bots.]
2. Append the bot token to the config file (`telegram -> bot -> tokens`)


## Config fields explanation

- telegram

  - account/bot:
    - session_file: The location to store the session data.

- tgfs

  - users: the users authenticated by tgfs, used by both webdav authentication and monitor
  - download
    - chunk_size_kb: The chunk size in KB when downloading files. Bigger chunk size means less requests.

- webdav
  - host: The host of the WebDAV server listening on.
  - port: The port of the WebDAV server listening on.
  - path: The root path for the WebDAV server. For example, setting this value to /webdav makes the WebDAV link `http://[host]:[port]/webdav`.

## FAQ

**Q: Why do I need a bot when my account is also able to send messages?**

Frequently sending messages may get your account banned, so using a bot is the best way to manage the risk. You can create another bot when it is banned.

**Q: Why do I need an account API then?**

The functionality of bot API is limited. For example, a bot can neither read history messages, nor send files exceeding 50MB. The account API is used when a bot cannot do the job.
