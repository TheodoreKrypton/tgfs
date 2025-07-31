import asyncio
import logging
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from tgfs.tasks import task_store

logger = logging.getLogger(__name__)


def create_manager_app() -> FastAPI:
    app = FastAPI(
        title="TGFS Task Manager",
        description="Task management API for TGFS upload/download operations",
        version="1.0.0",
    )

    # Enable CORS for the telegram mini-app
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, specify the exact origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health_check():
        return {"status": "healthy"}

    @app.get("/tasks", response_model=List[dict])
    async def get_tasks(path: Optional[str] = Query(None, description="Filter tasks under specific path")):
        """
        Get tasks. If path is provided, returns only tasks directly under that path.
        If no path is provided, returns all tasks.
        """
        try:
            if path is not None:
                tasks = await task_store.get_tasks_under_path(path)
            else:
                tasks = await task_store.get_all_tasks()

            return [task.to_dict() for task in tasks]
        except Exception as e:
            logger.error(f"Error getting tasks: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    @app.get("/tasks/{task_id}", response_model=dict)
    async def get_task(task_id: str):
        """Get a specific task by ID."""
        try:
            task = await task_store.get_task(task_id)
            if task is None:
                raise HTTPException(status_code=404, detail="Task not found")
            return task.to_dict()
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting task {task_id}: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    @app.delete("/tasks/{task_id}")
    async def delete_task(task_id: str):
        """Delete a task."""
        try:
            success = await task_store.remove_task(task_id)
            if not success:
                raise HTTPException(status_code=404, detail="Task not found")
            return {"message": "Task deleted successfully"}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting task {task_id}: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    @app.post("/tasks/cleanup")
    async def cleanup_tasks(max_age_hours: int = Query(24, description="Maximum age in hours for completed tasks")):
        """Clean up completed and failed tasks older than specified hours."""
        try:
            removed_count = await task_store.cleanup_completed_tasks(max_age_hours)
            return {"message": f"Cleaned up {removed_count} tasks"}
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    # Background task to periodically clean up old tasks
    @app.on_event("startup")
    async def startup_event():
        async def periodic_cleanup():
            while True:
                try:
                    await asyncio.sleep(3600)  # Run every hour
                    await task_store.cleanup_completed_tasks(24)
                except Exception as e:
                    logger.error(f"Error in periodic cleanup: {e}")
        
        # Start the cleanup task in the background
        asyncio.create_task(periodic_cleanup())

    return app