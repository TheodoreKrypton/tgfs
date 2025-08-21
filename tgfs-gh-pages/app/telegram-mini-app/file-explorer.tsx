"use client";

import {
  Close,
  CreateNewFolder,
  Delete,
  Download,
  FileUpload,
  Folder,
  Home,
  InsertDriveFile,
  MoreVert,
  Refresh,
  Telegram,
} from "@mui/icons-material";
import {
  Alert,
  Box,
  Breadcrumbs,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Fab,
  IconButton,
  Link,
  Menu,
  MenuItem,
  Paper,
  Snackbar,
  TextField,
  Typography,
} from "@mui/material";
import { SimpleTreeView } from "@mui/x-tree-view/SimpleTreeView";
import { TreeItem } from "@mui/x-tree-view/TreeItem";
import { useCallback, useEffect, useState } from "react";
import ManagerClient, { Task } from "./manager-client";
import TelegramImportDialog from "./telegram-import-dialog";
import WebDAVClient, { WebDAVItem } from "./webdav-client";

interface FileExplorerProps {
  webdavClient: WebDAVClient;
  managerClient: ManagerClient;
}

export default function FileExplorer({
  webdavClient,
  managerClient,
}: FileExplorerProps) {
  const [currentPath, setCurrentPath] = useState("/");
  const [items, setItems] = useState<WebDAVItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [selectedItem, setSelectedItem] = useState<WebDAVItem | null>(null);
  const [createDirDialog, setCreateDirDialog] = useState(false);
  const [newDirName, setNewDirName] = useState("");
  const [uploadDialog, setUploadDialog] = useState(false);
  const [telegramLinkDialog, setTelegramLinkDialog] = useState(false);
  const [snackbar, setSnackbar] = useState<{
    open: boolean;
    message: string;
    severity: "success" | "error";
  }>({
    open: false,
    message: "",
    severity: "success",
  });
  const [tasks, setTasks] = useState<Task[]>([]);

  const loadDirectory = useCallback(
    async (path: string) => {
      setLoading(true);
      setError(null);
      try {
        const directoryItems = await webdavClient.listDirectory(path);
        setItems(directoryItems);
        setCurrentPath(path);

        // Also load tasks for this directory if task manager is available
        if (managerClient) {
          try {
            const directoryTasks = await managerClient.getTasksUnderPath(path);
            setTasks(directoryTasks);
          } catch (taskErr) {
            console.warn("Failed to load tasks:", taskErr);
          }
        }
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to load directory"
        );
      } finally {
        setLoading(false);
      }
    },
    [webdavClient, managerClient]
  );

  // Load tasks for current directory
  const loadTasks = useCallback(async () => {
    if (managerClient) {
      try {
        const directoryTasks = await managerClient.getTasksUnderPath(
          currentPath
        );
        setTasks(directoryTasks);
      } catch (taskErr) {
        console.warn("Failed to load tasks:", taskErr);
      }
    }
  }, [managerClient, currentPath]);

  useEffect(() => {
    if (webdavClient) {
      loadDirectory("/");
    }
  }, [webdavClient, loadDirectory]);

  // Set up polling for task updates every 1 second
  useEffect(() => {
    const interval = setInterval(() => {
      loadTasks();
    }, 1000);

    return () => clearInterval(interval);
  }, [loadTasks]);

  const handleItemClick = useCallback(
    (item: WebDAVItem) => {
      if (item.isDirectory) {
        loadDirectory(item.path);
      }
    },
    [loadDirectory]
  );

  const handleMenuOpen = useCallback(
    (event: React.MouseEvent<HTMLElement>, item: WebDAVItem) => {
      if (item.isDirectory) return;

      event.stopPropagation();
      setAnchorEl(event.currentTarget);
      setSelectedItem(item);
    },
    []
  );

  const handleMenuClose = useCallback(() => {
    setAnchorEl(null);
    setSelectedItem(null);
  }, []);

  const handleDownload = useCallback(async () => {
    if (!selectedItem || selectedItem.isDirectory) return;

    try {
      const blob = await webdavClient.downloadFile(selectedItem.path);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = selectedItem.name;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);

      setSnackbar({
        open: true,
        message: `Downloaded ${selectedItem.name}`,
        severity: "success",
      });
    } catch (err) {
      setSnackbar({
        open: true,
        message: err instanceof Error ? err.message : "Download failed",
        severity: "error",
      });
    }
    handleMenuClose();
  }, [selectedItem, webdavClient, handleMenuClose]);

  const handleDelete = useCallback(async () => {
    if (!selectedItem) return;

    try {
      await webdavClient.deleteItem(selectedItem.path);
      await loadDirectory(currentPath);
      setSnackbar({
        open: true,
        message: `Deleted ${selectedItem.name}`,
        severity: "success",
      });
    } catch (err) {
      setSnackbar({
        open: true,
        message: err instanceof Error ? err.message : "Delete failed",
        severity: "error",
      });
    }
    handleMenuClose();
  }, [selectedItem, webdavClient, handleMenuClose, currentPath, loadDirectory]);

  const handleCreateDirectory = useCallback(async () => {
    if (!newDirName.trim()) return;

    try {
      const newPath = `${currentPath}${
        currentPath.endsWith("/") ? "" : "/"
      }${newDirName}`;
      await webdavClient.createDirectory(newPath);
      await loadDirectory(currentPath);
      setSnackbar({
        open: true,
        message: `Created directory ${newDirName}`,
        severity: "success",
      });
    } catch (err) {
      setSnackbar({
        open: true,
        message: err instanceof Error ? err.message : "Create directory failed",
        severity: "error",
      });
    }
    setCreateDirDialog(false);
    setNewDirName("");
  }, [currentPath, webdavClient, loadDirectory, newDirName]);

  const handleTelegramImport = useCallback(
    async (channelId: number, messageId: number, asName: string) => {
      if (!messageId || !currentPath) return;

      await managerClient.importTelegramMessage(
        channelId,
        messageId,
        currentPath,
        asName
      );
      setTelegramLinkDialog(false);
      await loadDirectory(currentPath);
      setSnackbar({
        open: true,
        message: `Imported message as ${asName}`,
        severity: "success",
      });
    },
    [managerClient, currentPath, loadDirectory]
  );

  const handleDeleteTask = useCallback(
    async (taskId: string, filename: string) => {
      try {
        await managerClient.deleteTask(taskId);
        await loadTasks(); // Refresh tasks after deletion
        setSnackbar({
          open: true,
          message: `Removed task ${filename}`,
          severity: "success",
        });
      } catch (err) {
        setSnackbar({
          open: true,
          message: err instanceof Error ? err.message : "Failed to remove task",
          severity: "error",
        });
      }
    },
    [managerClient, loadTasks]
  );

  const getPathParts = useCallback(() => {
    const parts = currentPath.split("/").filter(Boolean);
    return [
      { name: "Home", path: "/" },
      ...parts.map((part, index) => ({
        name: part,
        path: "/" + parts.slice(0, index + 1).join("/"),
      })),
    ];
  }, [currentPath]);

  const getFileIcon = useCallback((item: WebDAVItem) => {
    if (item.isDirectory) {
      return <Folder sx={{ color: "primary.main" }} />;
    }
    return <InsertDriveFile sx={{ color: "text.secondary" }} />;
  }, []);

  const getFileInfo = useCallback(
    (item: WebDAVItem) => {
      if (item.isDirectory) {
        return "Directory";
      }

      const parts = [];
      if (item.size !== undefined) {
        parts.push(webdavClient.formatFileSize(item.size));
      }
      if (item.lastModified) {
        parts.push(webdavClient.formatDate(item.lastModified));
      }
      return parts.join(" • ");
    },
    [webdavClient]
  );

  const renderTaskItem = useCallback(
    (task: Task) => (
      <TreeItem
        key={`task-${task.id}`}
        itemId={`task-${task.id}`}
        label={
          <Box sx={{ display: "flex", alignItems: "center", py: 1, pl: 2 }}>
            <Box sx={{ mr: 1, fontSize: "1rem" }}>
              {managerClient?.getTaskTypeIcon(task.type)}
            </Box>
            <Box sx={{ flexGrow: 1 }}>
              <Typography
                variant="body2"
                sx={{
                  fontStyle: "italic",
                  color: managerClient?.getTaskStatusColor(task.status),
                }}
              >
                {task.filename}
              </Typography>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                <Typography variant="caption" color="text.secondary">
                  {task.status} • {managerClient?.formatProgress(task.progress)}
                  {task.status === "in_progress" &&
                    task.speed_bytes_per_sec && (
                      <>
                        {" "}
                        • {managerClient?.formatSpeed(task.speed_bytes_per_sec)}
                      </>
                    )}
                </Typography>
                {task.status === "in_progress" && (
                  <CircularProgress
                    size={12}
                    variant="determinate"
                    value={task.progress * 100}
                  />
                )}
              </Box>
              {task.size_total && (
                <Typography variant="caption" color="text.secondary">
                  {managerClient?.formatFileSize(task.size_processed)} /{" "}
                  {managerClient?.formatFileSize(task.size_total)}
                </Typography>
              )}
            </Box>

            <IconButton
              size="small"
              onClick={(e) => {
                e.stopPropagation();
                handleDeleteTask(task.id, task.filename);
              }}
              sx={{ ml: 1 }}
              title="Remove task"
            >
              <Close fontSize="small" sx={{ color: "text.secondary" }} />
            </IconButton>
          </Box>
        }
      />
    ),
    [managerClient, handleDeleteTask]
  );

  const renderTreeItems = useCallback(
    (items: WebDAVItem[]) => {
      const fileItems = items.map((item) => (
        <TreeItem
          key={item.path}
          itemId={item.path}
          label={
            <Box
              sx={{ display: "flex", alignItems: "center", py: 1 }}
              onClick={() => handleItemClick(item)}
            >
              <Box sx={{ mr: 1 }}>{getFileIcon(item)}</Box>
              <Box sx={{ flexGrow: 1 }}>
                <Typography
                  variant="body2"
                  sx={{
                    cursor: "pointer",
                    fontWeight: item.isDirectory ? 500 : 400,
                  }}
                >
                  {item.name}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {getFileInfo(item)}
                </Typography>
              </Box>
              <IconButton
                size="small"
                onClick={(e) => handleMenuOpen(e, item)}
                sx={{ ml: 1 }}
              >
                <MoreVert fontSize="small" sx={{ color: "text.secondary" }} />
              </IconButton>
            </Box>
          }
        />
      ));

      const taskItems = tasks.map(renderTaskItem);

      // Combine and return all items
      return [...fileItems, ...taskItems];
    },
    [
      tasks,
      getFileIcon,
      getFileInfo,
      handleItemClick,
      handleMenuOpen,
      renderTaskItem,
    ]
  );

  return (
    <Box
      sx={{
        flex: 1,
        display: "flex",
        flexDirection: "column",
        maxHeight: "calc(100vh - 120px)",
      }}
    >
      <Box sx={{ p: 2, borderBottom: 1, borderColor: "divider" }}>
        <Breadcrumbs separator="›" sx={{ mb: 1 }}>
          {getPathParts().map((part, index) => (
            <Link
              key={part.path}
              component="button"
              variant="body2"
              onClick={() => loadDirectory(part.path)}
              sx={{ display: "flex", alignItems: "center", gap: 0.5 }}
            >
              {index === 0 && (
                <Home fontSize="small" sx={{ color: "text.primary" }} />
              )}
              {part.name}
            </Link>
          ))}
        </Breadcrumbs>

        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <Typography variant="h6" component="h2" sx={{ flexGrow: 1 }}>
            {items.length} items
          </Typography>
          <IconButton onClick={() => loadDirectory(currentPath)} size="small">
            <Refresh sx={{ color: "text.primary" }} />
          </IconButton>
        </Box>
      </Box>

      {loading && (
        <Box
          sx={{
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            flexGrow: 1,
          }}
        >
          <CircularProgress />
        </Box>
      )}

      {error && (
        <Alert severity="error" sx={{ m: 2 }}>
          {error}
        </Alert>
      )}

      {!loading && !error && (
        <Paper sx={{ flexGrow: 1, overflow: "auto", m: 2 }}>
          <SimpleTreeView>{renderTreeItems(items)}</SimpleTreeView>
        </Paper>
      )}

      <Box sx={{ position: "fixed", bottom: 16, right: 16 }}>
        <Fab
          color="primary"
          aria-label="add"
          onClick={() => setCreateDirDialog(true)}
          sx={{ mr: 1 }}
        >
          <CreateNewFolder />
        </Fab>
        <Fab
          color="secondary"
          aria-label="upload"
          onClick={() => setUploadDialog(true)}
        >
          <FileUpload />
        </Fab>
      </Box>

      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
      >
        {!selectedItem?.isDirectory && (
          <MenuItem onClick={handleDownload}>
            <Download sx={{ mr: 1, color: "text.primary" }} />
            Download
          </MenuItem>
        )}
        <MenuItem onClick={handleDelete}>
          <Delete sx={{ mr: 1, color: "text.primary" }} />
          Delete
        </MenuItem>
      </Menu>

      <Dialog open={createDirDialog} onClose={() => setCreateDirDialog(false)}>
        <DialogTitle>Create New Directory</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            label="Directory Name"
            value={newDirName}
            onChange={(e) => setNewDirName(e.target.value)}
            fullWidth
            margin="normal"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDirDialog(false)}>Cancel</Button>
          <Button onClick={handleCreateDirectory} disabled={!newDirName.trim()}>
            Create
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={uploadDialog} onClose={() => setUploadDialog(false)}>
        <DialogTitle>Upload File</DialogTitle>
        <DialogContent>
          <Box sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
            <Button
              variant="outlined"
              startIcon={<FileUpload />}
              onClick={() => {
                setUploadDialog(false);
                // Open file picker dialog
                const input = document.createElement("input");
                input.type = "file";
                input.onchange = async (e) => {
                  const file = (e.target as HTMLInputElement).files?.[0];
                  if (file) {
                    // Directly upload the file without setting state
                    try {
                      const filePath = `${currentPath}${
                        currentPath.endsWith("/") ? "" : "/"
                      }${file.name}`;
                      await webdavClient.uploadFile(filePath, file);
                      await loadDirectory(currentPath);
                      setSnackbar({
                        open: true,
                        message: `Uploaded ${file.name}`,
                        severity: "success",
                      });
                    } catch (err) {
                      setSnackbar({
                        open: true,
                        message:
                          err instanceof Error ? err.message : "Upload failed",
                        severity: "error",
                      });
                    }
                  }
                };
                input.click();
              }}
              fullWidth
            >
              Upload from Device
            </Button>

            {managerClient && (
              <Button
                variant="outlined"
                startIcon={<Telegram />}
                onClick={() => {
                  setUploadDialog(false);
                  setTelegramLinkDialog(true);
                }}
                fullWidth
              >
                Import from Telegram Message
              </Button>
            )}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setUploadDialog(false)}>Cancel</Button>
        </DialogActions>
      </Dialog>

      <TelegramImportDialog
        open={telegramLinkDialog}
        onClose={() => setTelegramLinkDialog(false)}
        onImport={handleTelegramImport}
        managerClient={managerClient}
      />

      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
        message={snackbar.message}
      />
    </Box>
  );
}
