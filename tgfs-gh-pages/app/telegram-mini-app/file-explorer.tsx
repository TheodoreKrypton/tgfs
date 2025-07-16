"use client";

import {
  CreateNewFolder,
  Delete,
  Download,
  FileUpload,
  Folder,
  Home,
  InsertDriveFile,
  MoreVert,
  Refresh,
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
import { useEffect, useState, useCallback } from "react";
import WebDAVClient, { WebDAVItem } from "./webdav-client";

interface FileExplorerProps {
  webdavClient: WebDAVClient;
}

export default function FileExplorer({ webdavClient }: FileExplorerProps) {
  const [currentPath, setCurrentPath] = useState("/");
  const [items, setItems] = useState<WebDAVItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [selectedItem, setSelectedItem] = useState<WebDAVItem | null>(null);
  const [createDirDialog, setCreateDirDialog] = useState(false);
  const [newDirName, setNewDirName] = useState("");
  const [uploadDialog, setUploadDialog] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [snackbar, setSnackbar] = useState<{
    open: boolean;
    message: string;
    severity: "success" | "error";
  }>({
    open: false,
    message: "",
    severity: "success",
  });

  const loadDirectory = useCallback(async (path: string) => {
    setLoading(true);
    setError(null);
    try {
      const directoryItems = await webdavClient.listDirectory(path);
      setItems(directoryItems);
      setCurrentPath(path);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load directory");
    } finally {
      setLoading(false);
    }
  }, [webdavClient]);

  useEffect(() => {
    if (webdavClient) {
      loadDirectory("/");
    }
  }, [webdavClient, loadDirectory]);

  const handleItemClick = (item: WebDAVItem) => {
    if (item.isDirectory) {
      loadDirectory(item.path);
    }
  };

  const handleMenuOpen = (
    event: React.MouseEvent<HTMLElement>,
    item: WebDAVItem
  ) => {
    event.stopPropagation();
    setAnchorEl(event.currentTarget);
    setSelectedItem(item);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
    setSelectedItem(null);
  };

  const handleDownload = async () => {
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
  };

  const handleDelete = async () => {
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
  };

  const handleCreateDirectory = async () => {
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
  };

  const handleFileUpload = async () => {
    if (!selectedFile) return;

    try {
      const filePath = `${currentPath}${currentPath.endsWith("/") ? "" : "/"}${
        selectedFile.name
      }`;
      await webdavClient.uploadFile(filePath, selectedFile);
      await loadDirectory(currentPath);
      setSnackbar({
        open: true,
        message: `Uploaded ${selectedFile.name}`,
        severity: "success",
      });
    } catch (err) {
      setSnackbar({
        open: true,
        message: err instanceof Error ? err.message : "Upload failed",
        severity: "error",
      });
    }
    setUploadDialog(false);
    setSelectedFile(null);
  };

  const getPathParts = () => {
    const parts = currentPath.split("/").filter(Boolean);
    return [
      { name: "Home", path: "/" },
      ...parts.map((part, index) => ({
        name: part,
        path: "/" + parts.slice(0, index + 1).join("/"),
      })),
    ];
  };

  const getFileIcon = (item: WebDAVItem) => {
    if (item.isDirectory) {
      return <Folder color="primary" />;
    }
    return <InsertDriveFile color="action" />;
  };

  const getFileInfo = (item: WebDAVItem) => {
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
  };

  const renderTreeItems = (items: WebDAVItem[]) => {
    return items.map((item) => (
      <TreeItem
        key={item.path}
        itemId={item.path}
        label={
          <Box sx={{ display: "flex", alignItems: "center", py: 1 }}>
            <Box sx={{ mr: 1 }}>{getFileIcon(item)}</Box>
            <Box sx={{ flexGrow: 1 }}>
              <Typography
                variant="body2"
                sx={{
                  cursor: "pointer",
                  fontWeight: item.isDirectory ? 500 : 400,
                }}
                onClick={() => handleItemClick(item)}
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
              <MoreVert fontSize="small" />
            </IconButton>
          </Box>
        }
      />
    ));
  };

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
              {index === 0 && <Home fontSize="small" />}
              {part.name}
            </Link>
          ))}
        </Breadcrumbs>

        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <Typography variant="h6" component="h2" sx={{ flexGrow: 1 }}>
            {items.length} items
          </Typography>
          <IconButton onClick={() => loadDirectory(currentPath)} size="small">
            <Refresh />
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
            <Download sx={{ mr: 1 }} />
            Download
          </MenuItem>
        )}
        <MenuItem onClick={handleDelete}>
          <Delete sx={{ mr: 1 }} />
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
          <input
            type="file"
            onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
            style={{ marginTop: 16 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setUploadDialog(false)}>Cancel</Button>
          <Button onClick={handleFileUpload} disabled={!selectedFile}>
            Upload
          </Button>
        </DialogActions>
      </Dialog>

      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
        message={snackbar.message}
      />
    </Box>
  );
}
