import {
  AuthType,
  createClient,
  FileStat,
  WebDAVClient as WebDAVClientType,
} from "webdav";

export interface WebDAVItem {
  name: string;
  path: string;
  isDirectory: boolean;
  size?: number;
  lastModified?: string;
  contentType?: string;
}

export default class WebDAVClient {
  private client: WebDAVClientType;

  constructor(
    url: string,
    jwtToken: string,
    private onError?: (message: string) => void
  ) {
    this.client = createClient(url, {
      authType: AuthType.Token,
      token: {
        access_token: jwtToken,
        token_type: "Bearer",
      },
    });
  }

  private handleError(error: unknown): never {
    if (error instanceof Error) {
      this.onError?.(error.message);
      throw Error(`WebDAV error: ${error.message}`);
    }
    throw Error("Unknown WebDAV error");
  }

  async connect(): Promise<void> {
    try {
      await this.client.stat("/");
    } catch (error) {
      this.handleError(error);
    }
  }

  async listDirectory(path: string = "/"): Promise<WebDAVItem[]> {
    try {
      const contents = await this.client.getDirectoryContents(path);

      return (contents as FileStat[]).map((item) => ({
        name: item.basename,
        path: item.filename,
        isDirectory: item.type === "directory",
        size: item.type === "file" ? item.size : undefined,
        lastModified: item.lastmod,
        contentType: item.mime,
      }));
    } catch (error) {
      this.handleError(error);
    }
  }

  async downloadFile(path: string): Promise<Blob> {
    try {
      const arrayBuffer = await this.client.getFileContents(path, {
        format: "binary",
      });
      return new Blob([arrayBuffer as ArrayBuffer]);
    } catch (error) {
      this.handleError(error);
    }
  }

  async uploadFile(path: string, file: File): Promise<void> {
    try {
      const arrayBuffer = await file.arrayBuffer();
      await this.client.putFileContents(path, arrayBuffer);
    } catch (error) {
      this.handleError(error);
    }
  }

  async createDirectory(path: string): Promise<void> {
    try {
      await this.client.createDirectory(path);
    } catch (error) {
      this.handleError(error);
    }
  }

  async deleteItem(path: string): Promise<void> {
    try {
      await this.client.deleteFile(path);
    } catch (error) {
      this.handleError(error);
    }
  }

  formatFileSize(bytes: number): string {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  }

  formatDate(dateString: string): string {
    try {
      const date = new Date(dateString);
      return date.toLocaleString();
    } catch {
      return dateString;
    }
  }
}
