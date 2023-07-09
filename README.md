# tgfs

Use telegram as file storage

[![Test](https://github.com/TheodoreKrypton/tgfs/actions/workflows/test.yml/badge.svg)](https://github.com/TheodoreKrypton/tgfs/actions/workflows/test.yml) [![codecov](https://codecov.io/gh/TheodoreKrypton/tgfs/branch/master/graph/badge.svg?token=CM6TF4C9B9)](https://codecov.io/gh/TheodoreKrypton/tgfs)

Tested on Windows, Ubuntu, MacOS

## Installation

```bash
$ yarn install && yarn build
$ alias tgfs="yarn cmd"
```

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
