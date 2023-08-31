# tgfs

Use telegram as file storage, with a command line tool and WebDAV server. Refer to the [wiki page](https://github.com/TheodoreKrypton/tgfs/wiki/TGFS-Wiki) for more detail.

[![Test](https://github.com/TheodoreKrypton/tgfs/actions/workflows/test.yml/badge.svg)](https://github.com/TheodoreKrypton/tgfs/actions/workflows/test.yml) [![codecov](https://codecov.io/gh/TheodoreKrypton/tgfs/branch/master/graph/badge.svg?token=CM6TF4C9B9)](https://codecov.io/gh/TheodoreKrypton/tgfs) [![npm version](https://badge.fury.io/js/tgfs.svg)](https://www.npmjs.com/package/tgfs)

Tested on Windows, Ubuntu, MacOS

## Installation

### Through NPM

```bash
$ npm install tgfs
```

### Through Git

```bash
$ yarn install && yarn build
$ alias tgfs="yarn start:prod"
```

## Use it as a WebDAV server

```
$ tgfs -w
```

or

```
$ tgfs --webdav
```

Tested WebDAV Clients:

- [Cyberduck](https://cyberduck.io/)
- [Mountain Duck](https://mountainduck.io/)
- [File Stash](https://www.filestash.app/)
- [WinSCP](https://winscp.net/eng/index.php)
- [WebDAV Sync](http://www.re.be/webdav_sync/index.xhtml)
- [Joplin](https://joplinapp.org/)

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

## Step by Step Guide to Set up config

### Automatically:

A config file will be auto-generated when you run the program for the first time. Just follow the instructions to create a Telegram app and a private channel to store the files.

### Manually:

#### First step

1. Duplicate the `example-config.yaml` file and name it `config.yaml`
2. Go to [Here](https://my.telegram.org/apps), login with your phone number and create a Telegram app.
3. Copy the `api_id` and `api_hash` from the Telegram app page (step 2) to the config file (`telegram -> api_id / api_hash`)

#### Set up the channel to store files

1. Create a new Telegram private channel (New Channel in the menu on the left)
2. There should be a message like "Channel created". Right click the message and copy the post link.
3. The format of the link should be like `https://t.me/c/1234567/1`, where `1234567` is the channel id. Copy the channel id to the config file (`telegram -> private_file_channel`)

## Config fields explanation

- telegram

  - session_file: The file path to store the session data. If you want to use multiple accounts, you can set different session files for each account.
  - login_timeout: Time to wait before login attempt aborts (in milliseconds).

- tgfs

  - download
    - porgress: Whether to show a progress bar when downloading files
    - chunk_size_kb: The chunk size in KB when downloading files. Bigger chunk size means less requests.

- webdav
  - host: The host of the WebDAV server listening on.
  - port: The port of the WebDAV server listening on.
  - users: The users of the WebDAV server.
    - password: The password of the user.
