<p align="center">
  <img src="https://raw.githubusercontent.com/TheodoreKrypton/tgfs/master/tgfs.png" alt="logo" width="100"/>
</p>

[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white)](https://hub.docker.com/r/wheatcarrier/tgfs)
[![Telegram Group](https://img.shields.io/badge/telegram-group-blue?style=for-the-badge&logo=telegram)](https://theodorekrypton.github.io/tgfs/join-group)
[![Telegram Mini App](https://img.shields.io/badge/telegram-miniapp-blue?style=for-the-badge&logo=telegram)](https://theodorekrypton.github.io/tgfs/telegram-mini-app)
[![Codecov](https://img.shields.io/codecov/c/github/TheodoreKrypton/tgfs?style=for-the-badge)](https://codecov.io/gh/TheodoreKrypton/tgfs)

# tgfs

Telegram becomes a WebDAV server.

Refer to [getting started](https://theodorekrypton.github.io/tgfs/) for installation and usage. (Docker or other container engine is required)

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

## GitHub metadata cache contract

GitHub-backed metadata can opt into a persistent startup cache. The cache is an
accelerator only: a missing, unreadable, malformed, or unsupported-version cache
always causes the existing complete GitHub tree walk rather than serving an
incomplete directory graph.

- **Location:** `<DATA_DIR>/metadata-cache/<sanitized-repo-name>-<channel-id>.json`.
  The channel id is part of the name so channels sharing a TGFS data directory
  cannot collide. The cache directory is runtime data and must not be committed.
- **Envelope:** JSON with `cache_version: 1`, `repo`, `configured_ref`,
  `resolved_tree_sha`, UTC ISO-8601 `written_at`, and `metadata`, where
  `metadata` is `TGFSMetadata.to_dict()` output. Unknown versions are cache
  misses.
- **Freshness:** a 40-character hexadecimal configured ref is treated as an
  immutable commit SHA and is valid only when it matches `configured_ref` in
  the envelope; no GitHub request is needed. For a branch or tag, TGFS makes one
  `get_branch(ref).commit.commit.tree.sha` request at startup and uses the cache
  only when it equals `resolved_tree_sha`. A failed freshness check is a miss.
- **Writes:** after a successful TGFS metadata `push()`, TGFS replaces the cache
  atomically (temp file in the destination directory followed by `os.replace`).
  Cache-write failures are warnings and never turn a successful GitHub write
  into a failed one.
- **Reload behavior:** cached directories must be rebuilt as `GithubDirectory`
  objects, preserving GitHub-backed write operations after restart.

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
