"use client";

import { Attachment, CheckCircle, Storage } from "@mui/icons-material";
import {
  Box,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Paper,
  TextField,
  Typography,
} from "@mui/material";
import mime from "mime-types";
import { useCallback, useEffect, useState } from "react";
import ManagerClient, { ChannelMessage } from "./manager-client";

interface TelegramImportDialogProps {
  open: boolean;
  onClose: () => void;
  onImport: (
    channelId: number,
    messageId: number,
    asName: string
  ) => Promise<void>;
  managerClient: ManagerClient;
}

export default function TelegramImportDialog({
  open,
  onClose,
  onImport,
  managerClient,
}: TelegramImportDialogProps) {
  const [telegramLink, setTelegramLink] = useState("");
  const [messagePreview, setMessagePreview] = useState<ChannelMessage | null>(
    null
  );
  const [previewLoading, setPreviewLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const [channelId, setChannelId] = useState<number | null>(null);
  const [messageId, setMessageId] = useState<number | null>(null);
  const [asName, setAsName] = useState<string>("unnamed");

  const extractMessageInfo = useCallback(
    (telegramLink: string): { messageId: number; channelId: number } => {
      const url = new URL(telegramLink);
      const pathParts = url.pathname.split("/");

      // Find channel ID (after /c/)
      const cIndex = pathParts.findIndex((part) => part === "c");
      if (cIndex === -1 || cIndex >= pathParts.length - 2) {
        throw new Error("Invalid Telegram message link format");
      }

      const channelId = parseInt(pathParts[cIndex + 1]);
      const messageId = parseInt(pathParts[pathParts.length - 1]);

      if (isNaN(channelId) || isNaN(messageId)) {
        throw new Error("Invalid Telegram message link format");
      }

      return { messageId, channelId };
    },
    []
  );

  // Debounced preview function
  useEffect(() => {
    if (!telegramLink.trim()) {
      setMessagePreview(null);
      setPreviewLoading(false);
      return;
    }

    // Show loading spinner immediately when user types
    setPreviewLoading(true);
    setMessagePreview(null);

    const debounceTimer = setTimeout(async () => {
      if (!telegramLink.trim()) {
        setMessagePreview(null);
        setPreviewLoading(false);
        return;
      }

      try {
        const { channelId, messageId } = extractMessageInfo(telegramLink);

        if (!channelId || !messageId) {
          throw new Error("Invalid Telegram message link format");
        }

        const messageInfo = await managerClient.getMessage(
          channelId,
          messageId
        );

        setChannelId(channelId);
        setMessageId(messageId);
        setMessagePreview(messageInfo);
        setErrorMessage(null);
      } catch (error) {
        setMessagePreview(null);
        setErrorMessage(
          error instanceof Error ? error.message : "Unknown error"
        );
      } finally {
        setPreviewLoading(false);
      }
    }, 1000); // 1 second debounce

    return () => {
      clearTimeout(debounceTimer);
    };
  }, [telegramLink, managerClient, extractMessageInfo]);

  const resetDialog = useCallback(() => {
    setTelegramLink("");
    setMessagePreview(null);
    setPreviewLoading(false);
    setChannelId(null);
    setMessageId(null);
    setAsName("unnamed");
    onClose();
  }, [onClose]);

  const handleImport = useCallback(async () => {
    if (channelId && messageId && asName.trim().length > 0) {
      await onImport(channelId, messageId, asName);
      resetDialog();
    }
  }, [channelId, messageId, asName, onImport, resetDialog]);

  const sanitizeFileName = useCallback(
    (name: string | null | undefined): string => {
      // remove spaces and special characters, unicode characters are permitted
      return (
        name
          ?.replace(/[^a-zA-Z0-9_\u00A0-\uFFFF]/g, "_")
          .replace(/_{2,}/g, "_") // replace multiple underscores with single
          .trim() ?? "unnamed"
      );
    },
    []
  );

  useEffect(() => {
    if (messagePreview) {
      const fileType = mime.extension(messagePreview.mime_type) || "bin";
      setAsName(
        (sanitizeFileName(messagePreview.caption) || "unnamed") + `.${fileType}`
      );
    }
  }, [messagePreview, sanitizeFileName]);

  return (
    <Dialog open={open} onClose={resetDialog}>
      <DialogTitle>Import Telegram File</DialogTitle>
      <DialogContent>
        <TextField
          autoFocus
          label="Telegram Message Link"
          value={telegramLink}
          onChange={(e) => setTelegramLink(e.target.value)}
          fullWidth
          margin="normal"
          placeholder="https://t.me/c/1234567/123"
          helperText="Paste the link to a Telegram message containing a file"
          InputProps={{
            endAdornment: previewLoading && (
              <CircularProgress size={20} sx={{ color: "text.secondary" }} />
            ),
          }}
        />
        <TextField
          label="File Name"
          value={asName}
          onChange={(e) => setAsName(e.target.value)}
          fullWidth
          margin="normal"
          placeholder="unnamed"
        />

        {errorMessage && (
          <Paper
            elevation={2}
            sx={{
              mt: 3,
              p: 3,
              borderRadius: 2,
              border: 1,
              borderColor: "error.main",
              bgcolor: "error.50",
            }}
          >
            <Typography
              variant="h6"
              sx={{ color: "error.main", fontWeight: 600 }}
            >
              {errorMessage}
            </Typography>
          </Paper>
        )}

        {messagePreview && (
          <Paper
            elevation={2}
            sx={{
              mt: 3,
              p: 3,
              borderRadius: 2,
              border: 1,
              borderColor: "success.main",
              bgcolor: "success.50",
              position: "relative",
            }}
          >
            <Box sx={{ display: "flex", alignItems: "center", mb: 2 }}>
              <>
                <CheckCircle sx={{ color: "success.main", mr: 1 }} />
                <Typography
                  variant="h6"
                  sx={{ color: "success.main", fontWeight: 600 }}
                >
                  File Ready for Import
                </Typography>
              </>
            </Box>

            <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
              <>
                <Box sx={{ display: "flex", alignItems: "center" }}>
                  <Storage
                    sx={{ color: "text.secondary", mr: 1, fontSize: 18 }}
                  />
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{ mr: 1 }}
                  >
                    Size:
                  </Typography>
                  <Typography variant="body2" sx={{ fontWeight: 500 }}>
                    {managerClient?.formatFileSize(messagePreview.file_size)}
                  </Typography>
                </Box>
                <Box sx={{ display: "flex", alignItems: "center" }}>
                  <Attachment
                    sx={{ color: "text.secondary", mr: 1, fontSize: 18 }}
                  />
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{ mr: 1 }}
                  >
                    Type:
                  </Typography>
                  <Typography variant="body2" sx={{ fontWeight: 500 }}>
                    {messagePreview.mime_type}
                  </Typography>
                </Box>
              </>

              {messagePreview.caption && (
                <Box sx={{ mt: 1 }}>
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{ mb: 0.5, fontWeight: 500 }}
                  >
                    Caption:
                  </Typography>
                  <Typography
                    variant="body2"
                    sx={{
                      bgcolor: "background.paper",
                      p: 1.5,
                      borderRadius: 1,
                      border: 1,
                      borderColor: "divider",
                      fontStyle: "italic",
                      wordBreak: "break-word",
                    }}
                  >
                    {messagePreview.caption}
                  </Typography>
                </Box>
              )}
            </Box>
          </Paper>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={resetDialog}>Cancel</Button>
        <Button
          onClick={handleImport}
          disabled={!messagePreview}
          variant="contained"
        >
          Import File
        </Button>
      </DialogActions>
    </Dialog>
  );
}
