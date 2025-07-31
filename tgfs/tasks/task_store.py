import asyncio
import os
from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4

from .models import Task, TaskStatus, TaskType


class TaskStore:
    def __init__(self):
        self._tasks: Dict[str, Task] = {}
        self._lock = asyncio.Lock()

    async def add_task(
        self,
        task_type: TaskType,
        path: str,
        filename: str,
        size_total: Optional[int] = None,
    ) -> str:
        async with self._lock:
            task_id = str(uuid4())
            now = datetime.utcnow().isoformat()

            task = Task(
                id=task_id,
                type=task_type,
                path=path,
                filename=filename,
                status=TaskStatus.PENDING,
                progress=0.0,
                size_total=size_total,
                size_processed=0,
                created_at=now,
                updated_at=now,
            )

            self._tasks[task_id] = task
            return task_id

    async def update_task_progress(
        self,
        task_id: str,
        size_processed: Optional[int] = None,
        status: Optional[TaskStatus] = None,
        error_message: Optional[str] = None,
    ) -> bool:
        async with self._lock:
            if task_id not in self._tasks:
                return False

            task = self._tasks[task_id]

            # Calculate speed if size_processed is being updated
            if size_processed is not None and task.size_processed is not None:
                now = datetime.utcnow()
                if task.updated_at:
                    try:
                        last_update = datetime.fromisoformat(task.updated_at)
                        time_diff = (now - last_update).total_seconds()

                        if time_diff > 0 and size_processed > task.size_processed:
                            bytes_diff = size_processed - task.size_processed
                            task.speed_bytes_per_sec = bytes_diff / time_diff
                    except (ValueError, TypeError):
                        # If timestamp parsing fails, don't calculate speed
                        pass

            task.updated_at = datetime.utcnow().isoformat()

            if size_processed is not None:
                task.size_processed = size_processed
                # Auto-calculate progress based on size_processed and size_total
                if task.size_total and task.size_total > 0:
                    task.progress = min(1.0, task.size_processed / task.size_total)
                else:
                    # If no size_total, use status to determine progress
                    if status == TaskStatus.COMPLETED:
                        task.progress = 1.0
                    elif status == TaskStatus.FAILED:
                        task.progress = 0.0
                    # Otherwise keep current progress

            if status is not None:
                task.status = status
                # Ensure progress is consistent with status
                if status == TaskStatus.COMPLETED:
                    task.progress = 1.0

            if error_message is not None:
                task.error_message = error_message

            return True

    async def get_task(self, task_id: str) -> Optional[Task]:
        async with self._lock:
            return self._tasks.get(task_id)

    async def get_all_tasks(self) -> List[Task]:
        async with self._lock:
            return list(self._tasks.values())

    async def get_tasks_under_path(self, path: str) -> List[Task]:
        async with self._lock:
            normalized_path = path.rstrip("/")
            if normalized_path == "":
                normalized_path = "/"

            result = []
            for task in self._tasks.values():
                task_dir = os.path.dirname(task.path).rstrip("/")
                if task_dir == "" and normalized_path == "/":
                    result.append(task)
                elif task_dir == normalized_path:
                    result.append(task)

            return result

    async def remove_task(self, task_id: str) -> bool:
        async with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]
                return True
            return False

    async def cleanup_completed_tasks(self, max_age_hours: int = 24) -> int:
        async with self._lock:
            cutoff_time = datetime.utcnow().timestamp() - (max_age_hours * 3600)
            to_remove = []

            for task_id, task in self._tasks.items():
                if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                    if task.updated_at:
                        task_time = datetime.fromisoformat(task.updated_at).timestamp()
                        if task_time < cutoff_time:
                            to_remove.append(task_id)

            for task_id in to_remove:
                del self._tasks[task_id]

            return len(to_remove)


# Global task store instance
task_store = TaskStore()
