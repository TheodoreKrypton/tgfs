import * as fs from 'fs';

import { Api, TelegramClient } from 'telegram';
import { BotAuthParams, UserAuthParams } from 'telegram/client/auth';
import { StringSession } from 'telegram/sessions';

import * as input from 'input';

import { ITDLibClient } from 'src/api/interface';
import * as types from 'src/api/types';
import { Config } from 'src/config';
import { Logger } from 'src/utils/logger';
import { sleep } from 'src/utils/sleep';

type AuthDetails = {
  authParams: UserAuthParams | BotAuthParams;
  sessionFile: string;
};

const login =
  (getAuthDetails: (config: Config) => Promise<AuthDetails>) =>
  async (config: Config) => {
    const apiId = config.telegram.api_id;
    const apiHash = config.telegram.api_hash;

    const { authParams, sessionFile } = await getAuthDetails(config);

    if (fs.existsSync(sessionFile)) {
      const session = new StringSession(String(fs.readFileSync(sessionFile)));
      const client = new TelegramClient(session, apiId, apiHash, {
        connectionRetries: 5,
      });

      try {
        await Promise.race([client.connect(), sleep(300000)]);
        if (client.connected) {
          return client;
        }
        Logger.error('login timeout');
        process.exit(1);
      } catch (err) {
        Logger.error(err);
      }
    }

    const client = new TelegramClient(new StringSession(''), apiId, apiHash, {
      connectionRetries: 5,
    });

    await client.start(authParams);

    fs.writeFileSync(sessionFile, String(client.session.save()));

    return client;
  };

export const loginAsAccount = login(async (config: Config) => {
  return {
    authParams: {
      phoneNumber: async () => await input.text('phone number?'),
      password: async () => await input.text('password?'),
      phoneCode: async () => await input.text('one-time code?'),
      onError: (err) => Logger.error(err),
    },
    sessionFile: config.telegram.account.session_file,
  };
});

export const loginAsBot = login(async (config: Config) => {
  return {
    authParams: {
      botAuthToken: config.telegram.bot.token,
    },
    sessionFile: config.telegram.bot.session_file,
  };
});

export class GramJSApi implements ITDLibClient {
  constructor(protected readonly client: TelegramClient) {}

  private static transformMessages(
    messages: Api.Message[],
  ): types.GetMessagesResp {
    const res: types.GetMessagesResp = [];

    for (const message of messages) {
      if (!message) {
        continue;
      }
      const obj: types.MessageResp = {
        messageId: message.id,
      };
      if (message.text) {
        obj.text = message.text;
      }
      if (message.document) {
        obj.document = {
          id: message.document.id,
          accessHash: message.document.accessHash,
          fileReference: message.document.fileReference,
          size: message.document.size,
        };
      }
      res.push(obj);
    }
    return res;
  }

  public async getMessages(
    req: types.GetMessagesReq,
  ): Promise<types.GetMessagesResp> {
    const rsp = await this.client.getMessages(req.chatId, {
      ids: req.messageIds,
    });
    return GramJSApi.transformMessages(rsp);
  }

  public async searchMessages(
    req: types.SearchMessagesReq,
  ): Promise<types.GetMessagesResp> {
    const rsp = await this.client.getMessages(req.chatId, {
      search: req.search,
    });

    return GramJSApi.transformMessages(rsp);
  }

  public async getPinnedMessages(
    req: types.GetPinnedMessagesReq,
  ): Promise<types.GetMessagesResp> {
    const rsp = await this.client.getMessages(req.chatId, {
      filter: new Api.InputMessagesFilterPinned(),
    });

    return GramJSApi.transformMessages(rsp);
  }

  public async saveBigFilePart(
    req: types.SaveBigFilePartReq,
  ): Promise<types.SaveFilePartResp> {
    const rsp = await this.client.invoke(
      new Api.upload.SaveBigFilePart({
        fileId: req.fileId,
        filePart: req.filePart,
        fileTotalParts: req.fileTotalParts,
        bytes: req.bytes,
      }),
    );
    return {
      success: rsp,
    };
  }

  public async saveFilePart(
    req: types.SaveFilePartReq,
  ): Promise<types.SaveFilePartResp> {
    const rsp = await this.client.invoke(
      new Api.upload.SaveFilePart({
        fileId: req.fileId,
        filePart: req.filePart,
        bytes: req.bytes,
      }),
    );
    return {
      success: rsp,
    };
  }

  public async sendBigFile(req: types.SendFileReq) {
    const rsp = await this.client.sendFile(req.chatId, {
      file: new Api.InputFileBig({
        id: req.file.id,
        parts: req.file.parts,
        name: req.file.name,
      }),
      caption: req.caption,
    });
    return {
      messageId: rsp.id,
    };
  }

  public async sendSmallFile(req: types.SendFileReq) {
    const rsp = await this.client.sendFile(req.chatId, {
      file: new Api.InputFile({
        id: req.file.id,
        parts: req.file.parts,
        name: req.file.name,
        md5Checksum: '',
      }),
      caption: req.caption,
    });
    return {
      messageId: rsp.id,
    };
  }

  public async downloadFile(
    req: types.DownloadFileReq,
  ): Promise<types.DownloadFileResp> {
    const message = (
      await this.getMessages({
        chatId: req.chatId,
        messageIds: [req.messageId],
      })
    )[0];

    const chunkSize = req.chunkSize * 1024;

    let i = 0;

    const client = this.client;

    async function* chunks() {
      for await (const chunk of client.iterDownload({
        file: new Api.InputDocumentFileLocation({
          id: message.document.id,
          accessHash: message.document.accessHash,
          fileReference: message.document.fileReference,
          thumbSize: '',
        }),
        requestSize: chunkSize,
      })) {
        i += 1;
        yield Buffer.from(chunk);
      }
    }

    return {
      chunks: chunks(),
      size: message.document.size,
    };
  }
}
