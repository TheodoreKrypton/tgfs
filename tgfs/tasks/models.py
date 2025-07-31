from dataclasses import dataclass
from enum import Enum
from typing import Optional


class TaskType(str, Enum):
    UPLOAD = "upload"
    DOWNLOAD = "download"


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Task:
    id: str
    type: TaskType
    path: str
    filename: str
    status: TaskStatus
    progress: float  # 0.0 to 1.0
    size_total: Optional[int] = None
    size_processed: Optional[int] = None
    error_message: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    speed_bytes_per_sec: Optional[float] = None  # Current transfer speed in bytes/sec

    def to_dict(self):
        return {
            "id": self.id,
            "type": self.type.value,
            "path": self.path,
            "filename": self.filename,
            "status": self.status.value,
            "progress": self.progress,
            "size_total": self.size_total,
            "size_processed": self.size_processed,
            "error_message": self.error_message,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "speed_bytes_per_sec": self.speed_bytes_per_sec,
        }