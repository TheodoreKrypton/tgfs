from tgfs.tasks.models import Task, TaskStatus, TaskType


class TestTaskType:
    def test_task_type_values(self):
        assert TaskType.UPLOAD == "upload"
        assert TaskType.DOWNLOAD == "download"
    
    def test_task_type_is_string_enum(self):
        assert isinstance(TaskType.UPLOAD, str)
        assert isinstance(TaskType.DOWNLOAD, str)


class TestTaskStatus:
    def test_task_status_values(self):
        assert TaskStatus.PENDING == "pending"
        assert TaskStatus.IN_PROGRESS == "in_progress"
        assert TaskStatus.COMPLETED == "completed"
        assert TaskStatus.FAILED == "failed"
    
    def test_task_status_is_string_enum(self):
        assert isinstance(TaskStatus.PENDING, str)
        assert isinstance(TaskStatus.IN_PROGRESS, str)
        assert isinstance(TaskStatus.COMPLETED, str)
        assert isinstance(TaskStatus.FAILED, str)


class TestTask:
    def test_task_creation_minimal(self):
        task = Task(
            id="task-123",
            type=TaskType.UPLOAD,
            path="/uploads/test.txt",
            filename="test.txt",
            status=TaskStatus.PENDING,
            progress=0.0
        )
        
        assert task.id == "task-123"
        assert task.type == TaskType.UPLOAD
        assert task.path == "/uploads/test.txt"
        assert task.filename == "test.txt"
        assert task.status == TaskStatus.PENDING
        assert task.progress == 0.0
        assert task.size_total is None
        assert task.size_processed is None
        assert task.error_message is None
        assert task.created_at is None
        assert task.updated_at is None
        assert task.speed_bytes_per_sec is None

    def test_task_creation_full(self):
        task = Task(
            id="task-456",
            type=TaskType.DOWNLOAD,
            path="/downloads/file.bin",
            filename="file.bin",
            status=TaskStatus.IN_PROGRESS,
            progress=0.75,
            size_total=1024,
            size_processed=768,
            error_message=None,
            created_at="2023-01-01T12:00:00Z",
            updated_at="2023-01-01T12:05:00Z",
            speed_bytes_per_sec=153.6
        )
        
        assert task.id == "task-456"
        assert task.type == TaskType.DOWNLOAD
        assert task.path == "/downloads/file.bin"
        assert task.filename == "file.bin"
        assert task.status == TaskStatus.IN_PROGRESS
        assert task.progress == 0.75
        assert task.size_total == 1024
        assert task.size_processed == 768
        assert task.error_message is None
        assert task.created_at == "2023-01-01T12:00:00Z"
        assert task.updated_at == "2023-01-01T12:05:00Z"
        assert task.speed_bytes_per_sec == 153.6

    def test_task_to_dict_minimal(self):
        task = Task(
            id="task-789",
            type=TaskType.UPLOAD,
            path="/test/file.txt",
            filename="file.txt",
            status=TaskStatus.PENDING,
            progress=0.0
        )
        
        expected_dict = {
            "id": "task-789",
            "type": "upload",
            "path": "/test/file.txt",
            "filename": "file.txt",
            "status": "pending",
            "progress": 0.0,
            "size_total": None,
            "size_processed": None,
            "error_message": None,
            "created_at": None,
            "updated_at": None,
            "speed_bytes_per_sec": None,
        }
        
        assert task.to_dict() == expected_dict

    def test_task_to_dict_full(self):
        task = Task(
            id="task-full",
            type=TaskType.DOWNLOAD,
            path="/downloads/large.zip",
            filename="large.zip",
            status=TaskStatus.COMPLETED,
            progress=1.0,
            size_total=2048000,
            size_processed=2048000,
            error_message=None,
            created_at="2023-01-01T10:00:00Z",
            updated_at="2023-01-01T10:30:00Z",
            speed_bytes_per_sec=1138.133
        )
        
        expected_dict = {
            "id": "task-full",
            "type": "download",
            "path": "/downloads/large.zip",
            "filename": "large.zip",
            "status": "completed",
            "progress": 1.0,
            "size_total": 2048000,
            "size_processed": 2048000,
            "error_message": None,
            "created_at": "2023-01-01T10:00:00Z",
            "updated_at": "2023-01-01T10:30:00Z",
            "speed_bytes_per_sec": 1138.133,
        }
        
        assert task.to_dict() == expected_dict

    def test_task_to_dict_with_error(self):
        task = Task(
            id="task-error",
            type=TaskType.UPLOAD,
            path="/failed/file.txt",
            filename="file.txt",
            status=TaskStatus.FAILED,
            progress=0.5,
            size_total=1000,
            size_processed=500,
            error_message="Network timeout",
            created_at="2023-01-01T14:00:00Z",
            updated_at="2023-01-01T14:02:30Z",
            speed_bytes_per_sec=166.67
        )
        
        task_dict = task.to_dict()
        assert task_dict["error_message"] == "Network timeout"
        assert task_dict["status"] == "failed"
        assert task_dict["progress"] == 0.5

    def test_task_enum_serialization_in_to_dict(self):
        """Test that enums are properly serialized as strings in to_dict."""
        task = Task(
            id="enum-test",
            type=TaskType.UPLOAD,
            path="/test.txt",
            filename="test.txt",
            status=TaskStatus.IN_PROGRESS,
            progress=0.25
        )
        
        task_dict = task.to_dict()
        
        # Ensure enum values are serialized as strings
        assert isinstance(task_dict["type"], str)
        assert isinstance(task_dict["status"], str)
        assert task_dict["type"] == "upload"
        assert task_dict["status"] == "in_progress"