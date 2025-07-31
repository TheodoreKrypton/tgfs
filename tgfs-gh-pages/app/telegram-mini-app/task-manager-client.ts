export interface Task {
  id: string;
  type: 'upload' | 'download';
  path: string;
  filename: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  progress: number; // 0.0 to 1.0
  size_total?: number;
  size_processed?: number;
  error_message?: string;
  created_at?: string;
  updated_at?: string;
  speed_bytes_per_sec?: number;
}

export default class TaskManagerClient {
  private baseUrl: string;

  constructor(baseUrl: string = 'http://localhost:1901') {
    this.baseUrl = baseUrl;
  }

  private async makeRequest<T>(endpoint: string): Promise<T> {
    const response = await fetch(`${this.baseUrl}${endpoint}`);
    
    if (!response.ok) {
      throw new Error(`Task Manager API error: ${response.status} ${response.statusText}`);
    }
    
    return response.json();
  }

  async getAllTasks(): Promise<Task[]> {
    return this.makeRequest<Task[]>('/tasks');
  }

  async getTasksUnderPath(path: string): Promise<Task[]> {
    const encodedPath = encodeURIComponent(path);
    return this.makeRequest<Task[]>(`/tasks?path=${encodedPath}`);
  }

  async getTask(taskId: string): Promise<Task> {
    return this.makeRequest<Task>(`/tasks/${taskId}`);
  }

  async deleteTask(taskId: string): Promise<void> {
    const response = await fetch(`${this.baseUrl}/tasks/${taskId}`, {
      method: 'DELETE',
    });
    
    if (!response.ok) {
      throw new Error(`Failed to delete task: ${response.status} ${response.statusText}`);
    }
  }

  async cleanupTasks(maxAgeHours: number = 24): Promise<{ message: string }> {
    const response = await fetch(`${this.baseUrl}/tasks/cleanup?max_age_hours=${maxAgeHours}`, {
      method: 'POST',
    });
    
    if (!response.ok) {
      throw new Error(`Failed to cleanup tasks: ${response.status} ${response.statusText}`);
    }
    
    return response.json();
  }

  formatFileSize(bytes?: number): string {
    if (!bytes || bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  }

  formatProgress(progress: number): string {
    return `${Math.round(progress * 100)}%`;
  }

  formatSpeed(bytesPerSec?: number): string {
    if (!bytesPerSec || bytesPerSec === 0) return "";
    
    const k = 1024;
    const sizes = ["B/s", "KB/s", "MB/s", "GB/s"];
    const i = Math.floor(Math.log(bytesPerSec) / Math.log(k));
    const value = parseFloat((bytesPerSec / Math.pow(k, i)).toFixed(1));
    
    return `${value} ${sizes[i]}`;
  }

  formatDate(dateString?: string): string {
    if (!dateString) return '';
    try {
      const date = new Date(dateString);
      return date.toLocaleString();
    } catch {
      return dateString;
    }
  }

  getTaskStatusColor(status: string): string {
    switch (status) {
      case 'pending':
        return '#f59e0b'; // amber
      case 'in_progress':
        return '#3b82f6'; // blue
      case 'completed':
        return '#10b981'; // green
      case 'failed':
        return '#ef4444'; // red
      default:
        return '#6b7280'; // gray
    }
  }

  getTaskTypeIcon(type: string): string {
    switch (type) {
      case 'upload':
        return '↑';
      case 'download':
        return '↓';
      default:
        return '?';
    }
  }
}