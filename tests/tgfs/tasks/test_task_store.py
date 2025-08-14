import pytest
import asyncio
import datetime
from tgfs.tasks.task_store import TaskStore, utcnow
from tgfs.tasks.models import TaskStatus, TaskType


class TestUtcNow:
    def test_utcnow(self, mocker):
        mock_datetime = mocker.patch("tgfs.tasks.task_store.datetime")
        mock_now = mocker.Mock()
        mock_datetime.datetime.now.return_value = mock_now
        mock_datetime.UTC = datetime.UTC

        result = utcnow()

        mock_datetime.datetime.now.assert_called_once_with(datetime.UTC)
        assert result == mock_now


class TestTaskStore:
    @pytest.fixture
    def task_store_instance(self):
        """Create a fresh TaskStore instance for each test."""
        return TaskStore()

    @pytest.mark.asyncio
    async def test_add_task_upload(self, task_store_instance):
        task_id = await task_store_instance.add_task(
            task_type=TaskType.UPLOAD,
            path="/uploads/test.txt",
            filename="test.txt",
            size_total=1024,
        )

        assert task_id is not None
        assert len(task_id) > 0

        task = await task_store_instance.get_task(task_id)
        assert task is not None
        assert task.type == TaskType.UPLOAD
        assert task.path == "/uploads/test.txt"
        assert task.filename == "test.txt"
        assert task.status == TaskStatus.PENDING
        assert task.progress == 0.0
        assert task.size_total == 1024
        assert task.size_processed == 0
        assert task.created_at is not None
        assert task.updated_at is not None
        assert task.error_message is None

    @pytest.mark.asyncio
    async def test_add_task_download_without_size(self, task_store_instance):
        task_id = await task_store_instance.add_task(
            task_type=TaskType.DOWNLOAD, path="/downloads/file.bin", filename="file.bin"
        )

        task = await task_store_instance.get_task(task_id)
        assert task.type == TaskType.DOWNLOAD
        assert task.size_total is None

    @pytest.mark.asyncio
    async def test_get_task_not_found(self, task_store_instance):
        task = await task_store_instance.get_task("nonexistent-id")
        assert task is None

    @pytest.mark.asyncio
    async def test_update_task_progress_size_delta(self, task_store_instance):
        task_id = await task_store_instance.add_task(
            TaskType.UPLOAD, "/test/file.txt", "file.txt", size_total=1000
        )

        # Update with size delta
        success = await task_store_instance.update_task_progress(
            task_id, size_delta=250
        )
        assert success is True

        task = await task_store_instance.get_task(task_id)
        assert task.size_processed == 250
        assert task.progress == 0.25  # 250/1000

    @pytest.mark.asyncio
    async def test_update_task_progress_with_status(self, task_store_instance):
        task_id = await task_store_instance.add_task(
            TaskType.UPLOAD, "/test/file.txt", "file.txt"
        )

        # Update status to in_progress
        success = await task_store_instance.update_task_progress(
            task_id, status=TaskStatus.IN_PROGRESS
        )
        assert success is True

        task = await task_store_instance.get_task(task_id)
        assert task.status == TaskStatus.IN_PROGRESS

    @pytest.mark.asyncio
    async def test_update_task_progress_completed_sets_progress(
        self, task_store_instance
    ):
        task_id = await task_store_instance.add_task(
            TaskType.UPLOAD, "/test/file.txt", "file.txt", size_total=1000
        )

        # Mark as completed
        success = await task_store_instance.update_task_progress(
            task_id, status=TaskStatus.COMPLETED
        )
        assert success is True

        task = await task_store_instance.get_task(task_id)
        assert task.status == TaskStatus.COMPLETED
        assert task.progress == 1.0

    @pytest.mark.asyncio
    async def test_update_task_progress_with_error(self, task_store_instance):
        task_id = await task_store_instance.add_task(
            TaskType.UPLOAD, "/test/file.txt", "file.txt"
        )

        # Update with error
        success = await task_store_instance.update_task_progress(
            task_id, status=TaskStatus.FAILED, error_message="Connection timeout"
        )
        assert success is True

        task = await task_store_instance.get_task(task_id)
        assert task.status == TaskStatus.FAILED
        assert task.error_message == "Connection timeout"

    @pytest.mark.asyncio
    async def test_update_task_progress_nonexistent_task(self, task_store_instance):
        success = await task_store_instance.update_task_progress(
            "nonexistent-id", size_delta=100
        )
        assert success is False

    @pytest.mark.asyncio
    async def test_update_task_progress_without_size_total(self, task_store_instance):
        task_id = await task_store_instance.add_task(
            TaskType.UPLOAD, "/test/file.txt", "file.txt"  # No size_total
        )

        # Update with size delta but no size_total
        await task_store_instance.update_task_progress(task_id, size_delta=100)
        task = await task_store_instance.get_task(task_id)
        assert task.size_processed == 100
        assert task.progress == 0.0  # Progress unchanged without size_total

        # Mark as completed should set progress to 1.0
        await task_store_instance.update_task_progress(
            task_id, status=TaskStatus.COMPLETED
        )
        task = await task_store_instance.get_task(task_id)
        assert task.progress == 1.0

    @pytest.mark.asyncio
    async def test_update_task_progress_speed_calculation(
        self, task_store_instance, mocker
    ):
        mock_utcnow = mocker.patch("tgfs.tasks.task_store.utcnow")
        # Create task at time T0
        time_t0 = datetime.datetime(2023, 1, 1, 12, 0, 0, tzinfo=datetime.UTC)
        mock_utcnow.return_value = time_t0

        task_id = await task_store_instance.add_task(
            TaskType.UPLOAD, "/test/file.txt", "file.txt", size_total=1000
        )

        # First update at T0 + 1 second
        time_t1 = time_t0 + datetime.timedelta(seconds=1)
        mock_utcnow.return_value = time_t1

        await task_store_instance.update_task_progress(task_id, size_delta=100)

        task = await task_store_instance.get_task(task_id)
        assert task.speed_bytes_per_sec == 100.0  # 100 bytes in 1 second

    @pytest.mark.asyncio
    async def test_update_task_progress_speed_calculation_invalid_timestamp(
        self, task_store_instance
    ):
        task_id = await task_store_instance.add_task(
            TaskType.UPLOAD, "/test/file.txt", "file.txt", size_total=1000
        )

        # Corrupt the timestamp to trigger exception handling
        task = await task_store_instance.get_task(task_id)
        task.updated_at = "invalid-timestamp"

        # This should not crash due to exception handling
        success = await task_store_instance.update_task_progress(
            task_id, size_delta=100
        )
        assert success is True

        task = await task_store_instance.get_task(task_id)
        assert task.speed_bytes_per_sec is None

    @pytest.mark.asyncio
    async def test_update_task_progress_failed_status_with_no_size_total(
        self, task_store_instance
    ):
        task_id = await task_store_instance.add_task(
            TaskType.UPLOAD, "/test/file.txt", "file.txt"  # No size_total
        )

        # Update with failed status and size delta
        await task_store_instance.update_task_progress(
            task_id, size_delta=50, status=TaskStatus.FAILED
        )

        task = await task_store_instance.get_task(task_id)
        assert task.size_processed == 50
        assert (
            task.progress == 0.0
        )  # Failed status sets progress to 0 when no size_total

    @pytest.mark.asyncio
    async def test_get_all_tasks(self, task_store_instance):
        # Add multiple tasks
        task_id1 = await task_store_instance.add_task(
            TaskType.UPLOAD, "/test/file1.txt", "file1.txt"
        )
        task_id2 = await task_store_instance.add_task(
            TaskType.DOWNLOAD, "/test/file2.txt", "file2.txt"
        )

        all_tasks = await task_store_instance.get_all_tasks()
        assert len(all_tasks) == 2

        task_ids = [task.id for task in all_tasks]
        assert task_id1 in task_ids
        assert task_id2 in task_ids

    @pytest.mark.asyncio
    async def test_get_all_tasks_empty(self, task_store_instance):
        all_tasks = await task_store_instance.get_all_tasks()
        assert all_tasks == []

    @pytest.mark.asyncio
    async def test_get_tasks_under_path_root(self, task_store_instance):
        # Add tasks in different directories
        await task_store_instance.add_task(TaskType.UPLOAD, "/file1.txt", "file1.txt")
        await task_store_instance.add_task(
            TaskType.UPLOAD, "/subdir/file2.txt", "file2.txt"
        )
        await task_store_instance.add_task(
            TaskType.UPLOAD, "/another/file3.txt", "file3.txt"
        )

        # Get tasks under root path
        root_tasks = await task_store_instance.get_tasks_under_path("/")
        assert len(root_tasks) == 1
        assert root_tasks[0].filename == "file1.txt"

    @pytest.mark.asyncio
    async def test_get_tasks_under_path_specific_directory(self, task_store_instance):
        await task_store_instance.add_task(
            TaskType.UPLOAD, "/uploads/file1.txt", "file1.txt"
        )
        await task_store_instance.add_task(
            TaskType.UPLOAD, "/uploads/file2.txt", "file2.txt"
        )
        await task_store_instance.add_task(
            TaskType.UPLOAD, "/downloads/file3.txt", "file3.txt"
        )

        # Get tasks under uploads directory
        upload_tasks = await task_store_instance.get_tasks_under_path("/uploads")
        assert len(upload_tasks) == 2

        upload_filenames = [task.filename for task in upload_tasks]
        assert "file1.txt" in upload_filenames
        assert "file2.txt" in upload_filenames

    @pytest.mark.asyncio
    async def test_get_tasks_under_path_with_trailing_slash(self, task_store_instance):
        await task_store_instance.add_task(
            TaskType.UPLOAD, "/uploads/file1.txt", "file1.txt"
        )

        # Test with and without trailing slash
        tasks_with_slash = await task_store_instance.get_tasks_under_path("/uploads/")
        tasks_without_slash = await task_store_instance.get_tasks_under_path("/uploads")

        assert len(tasks_with_slash) == 1
        assert len(tasks_without_slash) == 1
        assert tasks_with_slash[0].filename == tasks_without_slash[0].filename

    @pytest.mark.asyncio
    async def test_get_tasks_under_path_empty_string(self, task_store_instance):
        await task_store_instance.add_task(TaskType.UPLOAD, "/file1.txt", "file1.txt")

        # Empty path should be treated as root
        tasks = await task_store_instance.get_tasks_under_path("")
        assert len(tasks) == 1

    @pytest.mark.asyncio
    async def test_remove_task_success(self, task_store_instance):
        task_id = await task_store_instance.add_task(
            TaskType.UPLOAD, "/test/file.txt", "file.txt"
        )

        # Remove the task
        success = await task_store_instance.remove_task(task_id)
        assert success is True

        # Verify task is gone
        task = await task_store_instance.get_task(task_id)
        assert task is None

    @pytest.mark.asyncio
    async def test_remove_task_not_found(self, task_store_instance):
        success = await task_store_instance.remove_task("nonexistent-id")
        assert success is False

    @pytest.mark.asyncio
    async def test_cleanup_completed_tasks(self, task_store_instance):
        # Use current time for this test - we'll create tasks with specific timestamps
        current_time = datetime.datetime.now(datetime.UTC)

        # Create old completed task (more than 24 hours ago)
        old_time = current_time - datetime.timedelta(hours=25)
        task_id1 = await task_store_instance.add_task(
            TaskType.UPLOAD, "/test/old.txt", "old.txt"
        )
        await task_store_instance.update_task_progress(
            task_id1, status=TaskStatus.COMPLETED
        )
        task1 = await task_store_instance.get_task(task_id1)
        task1.updated_at = old_time.isoformat()

        # Create recent completed task (less than 24 hours ago)
        recent_time = current_time - datetime.timedelta(hours=1)
        task_id2 = await task_store_instance.add_task(
            TaskType.UPLOAD, "/test/recent.txt", "recent.txt"
        )
        await task_store_instance.update_task_progress(
            task_id2, status=TaskStatus.COMPLETED
        )
        task2 = await task_store_instance.get_task(task_id2)
        task2.updated_at = recent_time.isoformat()

        # Create old failed task (more than 24 hours ago)
        task_id3 = await task_store_instance.add_task(
            TaskType.UPLOAD, "/test/failed.txt", "failed.txt"
        )
        await task_store_instance.update_task_progress(
            task_id3, status=TaskStatus.FAILED
        )
        task3 = await task_store_instance.get_task(task_id3)
        task3.updated_at = old_time.isoformat()

        # Create in-progress task (should not be cleaned up regardless of age)
        task_id4 = await task_store_instance.add_task(
            TaskType.UPLOAD, "/test/inprogress.txt", "inprogress.txt"
        )
        await task_store_instance.update_task_progress(
            task_id4, status=TaskStatus.IN_PROGRESS
        )

        # Cleanup with 24 hour threshold - should remove old completed and failed tasks
        removed_count = await task_store_instance.cleanup_completed_tasks(
            max_age_hours=24
        )
        assert removed_count == 2  # old completed and old failed

        # Verify which tasks remain
        assert (
            await task_store_instance.get_task(task_id1) is None
        )  # Old completed removed
        assert (
            await task_store_instance.get_task(task_id2) is not None
        )  # Recent completed kept
        assert (
            await task_store_instance.get_task(task_id3) is None
        )  # Old failed removed
        assert (
            await task_store_instance.get_task(task_id4) is not None
        )  # In-progress kept

    @pytest.mark.asyncio
    async def test_cleanup_completed_tasks_no_updated_at(self, task_store_instance):
        # Create task without updated_at timestamp
        task_id = await task_store_instance.add_task(
            TaskType.UPLOAD, "/test/file.txt", "file.txt"
        )
        await task_store_instance.update_task_progress(
            task_id, status=TaskStatus.COMPLETED
        )

        task = await task_store_instance.get_task(task_id)
        task.updated_at = None  # Remove timestamp

        # Cleanup should not remove tasks without timestamps
        removed_count = await task_store_instance.cleanup_completed_tasks()
        assert removed_count == 0
        assert await task_store_instance.get_task(task_id) is not None

    @pytest.mark.asyncio
    async def test_cleanup_completed_tasks_empty_store(self, task_store_instance):
        removed_count = await task_store_instance.cleanup_completed_tasks()
        assert removed_count == 0

    @pytest.mark.asyncio
    async def test_task_store_concurrency(self, task_store_instance):
        """Test that the lock prevents race conditions."""

        async def add_many_tasks():
            tasks = []
            for i in range(10):
                task_id = await task_store_instance.add_task(
                    TaskType.UPLOAD, f"/test/file{i}.txt", f"file{i}.txt"
                )
                tasks.append(task_id)
            return tasks

        # Run multiple concurrent operations
        results = await asyncio.gather(
            add_many_tasks(),
            add_many_tasks(),
        )

        # All tasks should be added successfully
        all_tasks = await task_store_instance.get_all_tasks()
        assert len(all_tasks) == 20

        # All task IDs should be unique
        task_ids = [task.id for task in all_tasks]
        assert len(set(task_ids)) == 20


class TestGlobalTaskStore:
    def test_global_task_store_exists(self):
        """Test that the global task_store instance exists."""
        from tgfs.tasks.task_store import task_store

        assert isinstance(task_store, TaskStore)
