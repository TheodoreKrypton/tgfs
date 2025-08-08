<p align="center">
  <img src="https://raw.githubusercontent.com/TheodoreKrypton/tgfs/master/tgfs.png" alt="logo" width="100"/>
</p>

[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white)](https://hub.docker.com/r/wheatcarrier/tgfs)
[![Telegram Group](https://img.shields.io/badge/telegram-group-blue?style=for-the-badge&logo=telegram)](https://theodorekrypton.github.io/tgfs/join-group)
[![Telegram Mini App](https://img.shields.io/badge/telegram-miniapp-blue?style=for-the-badge&logo=telegram)](https://theodorekrypton.github.io/tgfs/telegram-mini-app)

# tgfs

Telegram becomes a WebDAV server.

Refer to [getting started](https://theodorekrypton.github.io/tgfs/) for installation and usage.

Refer to the [wiki page](https://github.com/TheodoreKrypton/tgfs/wiki/TGFS-Wiki) for technical detail.

## Tested Clients
* [rclone](https://rclone.org/)
* [Cyberduck](https://cyberduck.io/)
* [WinSCP](https://winscp.net/)
* [Documents](https://readdle.com/documents) by Readdle
* [VidHub](https://okaapps.com/product/1659622164)

## Features
* Upload and download files to/from a private Telegram channel via WebDAV
* Group files on Telegram channels into folders
* Infinite versioning of files and folders (Folder versioning is only available when Metadata is maintained on Github repository)
* Importing files that are already on Telegram (Only via the Telegram Mini App)
* File size is unlimited (larger files are chunked into parts but appear as a single file to the user)
* Live streaming of videos


## Demo Server
* WebDAV URL: `https://tgfs-demo.wheatcarrier.site/webdav`
* `username` and `password` can be any
* File channel on Telegram: [@tgfsdemo](https://t.me/tgfsdemo)
* Github repository for metadata: [https://github.com/tgfs-demo/tgfs-demo](https://github.com/tgfs-demo/tgfs-demo)
* Config file: [config.yaml](https://github.com/TheodoreKrypton/tgfs/blob/master/demo-config.yaml)

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
