import * as types from './types';

export interface ITDLibApi {
  // getMe(): Promise<void>;
  // getPinnedMessage(): Promise<types.Message>;

  getMessages(req: types.GetMessagesReq): Promise<types.GetMessagesResp>;

  searchMessages(req: types.SearchMessagesReq): Promise<types.GetMessagesResp>;

  getPinnedMessages(
    req: types.GetPinnedMessagesReq,
  ): Promise<types.GetMessagesResp>;

  saveBigFilePart(
    req: types.SaveBigFilePartReq,
  ): Promise<types.SaveBigFilePartResp>;

  sendBigFile(req: types.SendBigFileReq): Promise<types.SendMessageResp>;

  sendFileFromPath(
    req: types.SendFileFromPathReq,
  ): Promise<types.SendMessageResp>;

  sendFileFromBuffer(
    req: types.SendFileFromBufferReq,
  ): Promise<types.SendMessageResp>;

  downloadFile(req: types.DownloadFileReq): types.DownloadFileResp;
}

export interface IBotApi {
  sendText(req: types.SendTextReq): Promise<types.SendMessageResp>;

  editMessageText(
    req: types.EditMessageTextReq,
  ): Promise<types.SendMessageResp>;

  editMessageMedia(
    req: types.EditMessageMediaReq,
  ): Promise<types.SendMessageResp>;

  sendFileFromPath(
    req: types.SendFileFromPathReq,
  ): Promise<types.SendMessageResp>;

  sendFileFromBuffer(
    req: types.SendFileFromBufferReq,
  ): Promise<types.SendMessageResp>;

  pinMessage(req: types.PinMessageReq): Promise<void>;
}
