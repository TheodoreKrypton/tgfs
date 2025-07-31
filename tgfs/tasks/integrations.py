import logging
import os
from typing import Optional

from .models import TaskStatus, TaskType
from .task_store import task_store

logger = logging.getLogger(__name__)


class TaskTracker:
    """Helper class to track upload/download tasks"""

    def __init__(self, task_id: str):
        self.task_id = task_id

    async def update_progress(
        self,
        size_processed: Optional[int] = None,
        status: Optional[TaskStatus] = None,
        error_message: Optional[str] = None,
    ):
        """Update task progress by size processed"""
        try:
            await task_store.update_task_progress(
                self.task_id, size_processed, status, error_message
            )
        except Exception as e:
            logger.error(f"Failed to update task progress for {self.task_id}: {e}")

    async def mark_completed(self):
        """Mark task as completed"""
        await self.update_progress(status=TaskStatus.COMPLETED)

    async def mark_failed(self, error_message: str):
        """Mark task as failed"""
        await self.update_progress(
            status=TaskStatus.FAILED,
            error_message=error_message,
        )


async def create_upload_task(file_path: str, file_size: Optional[int] = None) -> TaskTracker:
    """Create a new upload task and return a tracker"""
    filename = os.path.basename(file_path)
    task_id = await task_store.add_task(
        TaskType.UPLOAD, file_path, filename, file_size
    )
    
    # Mark as in progress immediately
    await task_store.update_task_progress(task_id, status=TaskStatus.IN_PROGRESS)
    
    return TaskTracker(task_id)


async def create_download_task(file_path: str, file_size: Optional[int] = None) -> TaskTracker:
    """Create a new download task and return a tracker"""
    filename = os.path.basename(file_path)
    task_id = await task_store.add_task(
        TaskType.DOWNLOAD, file_path, filename, file_size
    )
    
    # Mark as in progress immediately
    await task_store.update_task_progress(task_id, status=TaskStatus.IN_PROGRESS)
    
    return TaskTracker(task_id)