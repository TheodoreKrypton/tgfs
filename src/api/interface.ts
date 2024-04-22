import * as types from './types';

export interface ITDLibClient {
  // getMe(): Promise<void>;
  // getPinnedMessage(): Promise<types.Message>;

  getMessages(req: types.GetMessagesReq): Promise<types.GetMessagesResp>;

  sendText(req: types.SendTextReq): Promise<types.SendMessageResp>;

  editMessageText(
    req: types.EditMessageTextReq,
  ): Promise<types.SendMessageResp>;

  searchMessages(req: types.SearchMessagesReq): Promise<types.GetMessagesResp>;

  getPinnedMessages(
    req: types.GetPinnedMessagesReq,
  ): Promise<types.GetMessagesResp>;

  pinMessage(req: types.PinMessageReq): Promise<void>;

  saveBigFilePart(
    req: types.SaveBigFilePartReq,
  ): Promise<types.SaveFilePartResp>;

  saveFilePart(req: types.SaveFilePartReq): Promise<types.SaveFilePartResp>;

  sendBigFile(req: types.SendFileReq): Promise<types.SendMessageResp>;

  sendSmallFile(req: types.SendFileReq): Promise<types.SendMessageResp>;

  editMessageMedia(req: types.EditMessageMediaReq): Promise<types.Message>;

  downloadFile(req: types.DownloadFileReq): types.DownloadFileResp;
}

export interface IBot {}

export type TDLibApi = {
  account: ITDLibClient;
  bot: ITDLibClient;
};
