import logging
import os
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from tgfs.app.cache import fs_cache
from tgfs.config import Config
from tgfs.core import Client
from tgfs.core.ops import Ops
from tgfs.reqres import MessageRespWithDocument
from tgfs.tasks import task_store

logger = logging.getLogger(__name__)


def create_manager_app(client: Client, config: Config) -> FastAPI:
    ops = Ops(client)

    app = FastAPI()

    @app.get("/tasks", response_model=List[dict])
    async def get_tasks(
        path: Optional[str] = Query(
            None, description="Filter tasks under specific path"
        )
    ):
        if path is not None:
            tasks = await task_store.get_tasks_under_path(path)
        else:
            tasks = await task_store.get_all_tasks()

        return [task.to_dict() for task in tasks]

    @app.get("/tasks/{task_id}", response_model=dict)
    async def get_task(task_id: str):
        if not (task := await task_store.get_task(task_id)):
            raise HTTPException(status_code=404, detail="Task not found")
        return task.to_dict()

    @app.delete("/tasks/{task_id}")
    async def delete_task(task_id: str):
        """Delete a task."""
        if not await task_store.remove_task(task_id):
            raise HTTPException(status_code=404, detail="Task not found")
        return {"message": "Task deleted successfully"}

    async def get_message(channel_id: int, message_id: int) -> MessageRespWithDocument:
        """Helper function to get a message from the Telegram client."""
        expected_channel_id = int(config.telegram.private_file_channel)

        if channel_id != expected_channel_id:
            raise HTTPException(
                status_code=400,
                detail="The message is not in the configured file channel. Please forward the message to the file channel first.",
            )

        message = (await client.message_api.get_messages([message_id]))[0]

        if not message:
            raise HTTPException(
                status_code=404,
                detail=f"Message {message_id} not found in the file channel.",
            )

        if not message.document:
            raise HTTPException(
                status_code=400, detail="The message does not contain a document."
            )

        return MessageRespWithDocument(
            message_id=message.message_id,
            document=message.document,
            text=message.text,
        )

    @app.get("/message/{channel_id}/{message_id}")
    async def get_telegram_message(channel_id: int, message_id: int):
        message = await get_message(channel_id, message_id)

        # Return message info regardless of whether it has a document
        return {
            "id": message.message_id,
            "file_size": message.document.size,
            "caption": message.text or "",
            "has_document": message.document is not None,
            "mime_type": message.document.mime_type if message.document else None,
        }

    class ImportTelegramMessageData(BaseModel):
        directory: str
        name: str
        channel_id: int
        message_id: int

    @app.post("/import")
    async def import_telegram_message(body: ImportTelegramMessageData):
        path = os.path.join(body.directory, body.name)
        fs_cache.reset_parent(path)

        message = await get_message(body.channel_id, body.message_id)

        await ops.import_from_existing_file_message(
            message, os.path.join(body.directory, body.name)
        )

        return {"message": "Document imported successfully"}

    return app
