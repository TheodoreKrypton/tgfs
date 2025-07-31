<p align="center">
  <img src="https://raw.githubusercontent.com/TheodoreKrypton/tgfs/master/tgfs.png" alt="logo" width="100"/>
</p>

[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white)](https://hub.docker.com/r/wheatcarrier/tgfs)
[![Telegram Mini App](https://img.shields.io/badge/telegram-miniapp-blue?style=for-the-badge&logo=telegram)](https://t.me/tgfsprdbot/manager)
# tgfs

Telegram becomes a WebDAV server.

Refer to the [wiki page](https://github.com/TheodoreKrypton/tgfs/wiki/TGFS-Wiki) for technical detail.

## Installation

### Through Docker

You must prepare a directory (defaulted to .tgfs) to store the app data, and place a `config.yaml` file in it.

Refer to the [Set up config file](#set-up-config-file) section for creating the `config.yaml` file.

For the first time, you should run the command below to be prompted to enter phone number, verification code, etc. for the session file generation.
```bash
docker run -it \
  -v .tgfs:/home/tgfs/.tgfs \  # Volume to store app data. config.yaml is in this directory.
  -p 1900:1900 \
  wheatcarrier/tgfs
```

After the session file is generated, you can run the following command to start the tgfs server in detached mode.
```bash
docker run -d --name tgfs \
  -v .tgfs:/home/tgfs/.tgfs \  # Volume to store app data. config.yaml is in this directory.
  -p 1900:1900 \
  wheatcarrier/tgfs
```

## Client

You can use any WebDAV client to access the server.

Tested WebDAV Clients:
- [Cyberduck](https://cyberduck.io/)
- [WinSCP](https://winscp.net/eng/index.php)
- [rclone](https://rclone.org/)

### Official Telegram miniapp

You can also use the [official tgfs Telegram miniapp](https://t.me/tgfsprdbot/manager) to access the server.<br>
It is a pure frontend application, source code is available in [here](https://github.com/TheodoreKrypton/tgfs/tree/master/tgfs-gh-pages/app/telegram-mini-app), and it is deployed on [GitHub Pages](https://theodorekrypton.github.io/tgfs/telegram-mini-app).<br>
You can deploy your own version if you are worried about privacy.

## Set up config file

> **WARNING:** For feature development purpose, any configuration is **unstable** at the current stage. You may need to reconfigure following any update.

### Use Config Generator

You can use the [config generator](https://theodorekrypton.github.io/tgfs/config-generator/) to generate a `config.yaml` file.

### Manual Setup
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
  - users: The users authenticated by tgfs, used by both webdav authentication and monitor
  - download
    - chunk_size_kb: The chunk size in KB when downloading files. Bigger chunk size means less requests.
  - metadata: Metadata maintains the tree structure of the directories and files. There are two ways to store metadata:
    - pinned_message (default): The metadata is stored as a json file pinned in the file channel. Every directory operation updates/reupload the json file.
    - github_repo: The metadata is stored in a GitHub repository configured in the following `github_repo` section. Every directory operation is mapped to the github repository. Merits of this method include:
      - The tree structure is versioned naturally, so you can roll back to a previous version if something goes wrong.
      - Directory operations are faster (possibly?) because the metadata is not re-uploaded every time.
      - Multiple clients can access / mutates the same metadata without conflicts.

- webdav
  - host: The host of the WebDAV server listening on.
  - port: The port of the WebDAV server listening on.
  - path: The root path for the WebDAV server. For example, setting this value to /webdav makes the WebDAV link `http://[host]:[port]/webdav`.

- manager
  - host: The host of the manager server listening on.
  - port: The port of the manager server listening on.


## FAQ

**Q: Why do I need a bot when my account is also able to send messages?**

Frequently sending messages may get your account banned, so using a bot is the best way to manage the risk. You can create another bot when it is banned.

**Q: Why do I need an account API then?**

There are some API that are only available for user accounts.

## Development

Install the dependencies:
```bash
poetry install
```

Run the app:
```bash
poetry run python main.py
```

Typecheck && lint:
```bash
make mypy
make ruff
```

Before committing and pushing, run the following command to install git hooks:
```bash
pre-commit install
```
