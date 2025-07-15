import { createClient, WebDAVClient as WebDAVClientType, FileStat, AuthType } from 'webdav';

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

  constructor(baseUrl: string, username: string = "", password: string = "") {
    this.client = createClient(baseUrl, {
      authType: username ? AuthType.Password : AuthType.None,
      username,
      password,
    });
  }

  async connect(): Promise<void> {
    try {
      // Test connection by getting root directory info
      await this.client.stat('/');
    } catch (error) {
      if (error instanceof Error) {
        throw new Error(`Connection failed: ${error.message}`);
      }
      throw new Error("Failed to connect to WebDAV server");
    }
  }

  async listDirectory(path: string = "/"): Promise<WebDAVItem[]> {
    try {
      const contents = await this.client.getDirectoryContents(path);
      
      return (contents as FileStat[]).map((item) => ({
        name: item.basename,
        path: item.filename,
        isDirectory: item.type === 'directory',
        size: item.type === 'file' ? item.size : undefined,
        lastModified: item.lastmod,
        contentType: item.mime,
      }));
    } catch (error) {
      if (error instanceof Error) {
        throw new Error(`Failed to list directory: ${error.message}`);
      }
      throw new Error("Failed to list directory");
    }
  }

  async downloadFile(path: string): Promise<Blob> {
    try {
      const arrayBuffer = await this.client.getFileContents(path, { format: 'binary' });
      return new Blob([arrayBuffer as ArrayBuffer]);
    } catch (error) {
      if (error instanceof Error) {
        throw new Error(`Failed to download file: ${error.message}`);
      }
      throw new Error("Failed to download file");
    }
  }

  async uploadFile(path: string, file: File): Promise<void> {
    try {
      const arrayBuffer = await file.arrayBuffer();
      await this.client.putFileContents(path, arrayBuffer);
    } catch (error) {
      if (error instanceof Error) {
        throw new Error(`Failed to upload file: ${error.message}`);
      }
      throw new Error("Failed to upload file");
    }
  }

  async createDirectory(path: string): Promise<void> {
    try {
      await this.client.createDirectory(path);
    } catch (error) {
      if (error instanceof Error) {
        throw new Error(`Failed to create directory: ${error.message}`);
      }
      throw new Error("Failed to create directory");
    }
  }

  async deleteItem(path: string): Promise<void> {
    try {
      await this.client.deleteFile(path);
    } catch (error) {
      if (error instanceof Error) {
        throw new Error(`Failed to delete item: ${error.message}`);
      }
      throw new Error("Failed to delete item");
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