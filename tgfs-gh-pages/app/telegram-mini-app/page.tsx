"use client";

import {
  FolderOpen,
  Login,
  TaskAlt,
  Wifi,
  WifiOff,
  Telegram,
} from "@mui/icons-material";
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Container,
  CssBaseline,
  FormControlLabel,
  Paper,
  Switch,
  TextField,
  ThemeProvider,
  Typography,
  createTheme,
} from "@mui/material";
import Cookies from "js-cookie";
import React, { useEffect, useState } from "react";
import {
  miniApp,
  viewport,
  on,
  init,
  isTMA,
  retrieveLaunchParams,
} from "@telegram-apps/sdk";
import type { ThemeParams } from "@telegram-apps/types";
import FileExplorer from "./file-explorer";
import TaskManagerClient from "./task-manager-client";
import { telegramTheme } from "./telegram-theme";
import WebDAVClient from "./webdav-client";

interface LoginFormData {
  webdavUrl: string;
  username: string;
  password: string;
  anonymous: boolean;
  managerUrl: string;
  enableManager: boolean;
}

export default function TelegramMiniApp() {
  // State management
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [webdavClient, setWebdavClient] = useState<WebDAVClient | null>(null);
  const [taskManagerClient, setTaskManagerClient] =
    useState<TaskManagerClient | null>(null);
  const [isInTelegram, setIsInTelegram] = useState(false);
  const [telegramThemeColors, setTelegramThemeColors] =
    useState<ThemeParams | null>(null);
  const [formData, setFormData] = useState<LoginFormData>({
    webdavUrl: "",
    username: "",
    password: "",
    anonymous: false,
    managerUrl: "",
    enableManager: false,
  });

  // Session cleanup handler
  const handle401Error = () => {
    const cookiesToRemove = [
      "jwt_token",
      "webdav_url",
      "manager_url",
      "enable_manager",
    ];
    cookiesToRemove.forEach((cookie) => Cookies.remove(cookie));

    setIsLoggedIn(false);
    setWebdavClient(null);
    setTaskManagerClient(null);
    setError("Session expired. Please login again.");
  };

  // Initialize app on mount
  useEffect(() => {
    let removeThemeListener: (() => void) | null = null;

    // Initialize Telegram SDK using the standard pattern
    try {
      // First, initialize the SDK
      init();

      // Check if we're in Telegram environment using the official method
      const inTelegram = isTMA();
      setIsInTelegram(inTelegram);

      if (inTelegram) {
        miniApp.ready();
        viewport.expand();

        const launchParams = retrieveLaunchParams();
        setTelegramThemeColors(launchParams.tgWebAppThemeParams);
        document.body.style.backgroundColor =
          launchParams.tgWebAppThemeParams.bg_color || "";

        removeThemeListener = on("theme_changed", (eventData) => {
          const updatedTheme = eventData.theme_params;
          setTelegramThemeColors(updatedTheme);
          document.body.style.backgroundColor = updatedTheme.bg_color || "";
        });
      }
    } catch {
      setIsInTelegram(false);
    }

    // Restore session from cookies
    const token = Cookies.get("jwt_token");
    const savedWebdavUrl = Cookies.get("webdav_url");
    const savedManagerUrl = Cookies.get("manager_url");
    const savedEnableManager = Cookies.get("enable_manager") === "true";

    setFormData((prev) => ({
      ...prev,
      webdavUrl: savedWebdavUrl || "",
      enableManager: savedEnableManager,
    }));

    if (token && savedWebdavUrl) {
      const client = new WebDAVClient(savedWebdavUrl, token, handle401Error);
      setWebdavClient(client);

      if (savedEnableManager && savedManagerUrl) {
        const taskClient = new TaskManagerClient(savedManagerUrl);
        setTaskManagerClient(taskClient);
      }

      setIsLoggedIn(true);
    }

    // Cleanup function
    return () => {
      if (typeof removeThemeListener === "function") {
        removeThemeListener();
      }
    };
  }, []);

  const handleInputChange =
    (field: keyof LoginFormData) =>
    (event: React.ChangeEvent<HTMLInputElement>) => {
      const value =
        event.target.type === "checkbox"
          ? event.target.checked
          : event.target.value;
      setFormData((prev) => ({ ...prev, [field]: value }));
    };

  const handleLogin = async () => {
    setIsLoading(true);
    setError(null);

    try {
      // Send login request to get JWT token
      const response = await fetch(`${formData.webdavUrl}/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          username: formData.anonymous ? "" : formData.username,
          password: formData.anonymous ? "" : formData.password,
        }),
      });

      if (!response.ok) {
        throw new Error("Login failed");
      }

      const data = await response.json();
      const token = data.token;

      // Store JWT token and server info in cookies
      Cookies.set("jwt_token", token, { expires: 7 }); // 7 days expiry
      Cookies.set("webdav_url", formData.webdavUrl, { expires: 7 });
      Cookies.set("manager_url", formData.managerUrl, { expires: 7 });
      Cookies.set("enable_manager", formData.enableManager.toString(), {
        expires: 7,
      });

      // Create WebDAV client with JWT token
      const client = new WebDAVClient(
        formData.webdavUrl,
        token,
        handle401Error
      );
      await client.connect();
      setWebdavClient(client);

      // Initialize task manager client if enabled
      if (formData.enableManager) {
        const taskClient = new TaskManagerClient(formData.managerUrl);
        setTaskManagerClient(taskClient);
      }

      setIsLoggedIn(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setIsLoading(false);
    }
  };

  const handleLogout = () => {
    handle401Error();
    setError(null);
  };

  // Create dynamic theme based on Telegram theme parameters
  const currentTheme = React.useMemo(() => {
    if (isInTelegram && telegramThemeColors) {
      // Use actual Telegram colors with fallbacks only when not in Telegram
      const telegramBg = telegramThemeColors.bg_color || "#ffffff";
      const telegramPaper = telegramThemeColors.secondary_bg_color || "#f8f9fa";
      const telegramText = telegramThemeColors.text_color || "#000000";
      const telegramHint = telegramThemeColors.hint_color || "#6c757d";
      const telegramButton = telegramThemeColors.button_color || "#0088cc";
      const telegramLink = telegramThemeColors.link_color || "#0088cc";

      return createTheme({
        palette: {
          primary: {
            main: telegramButton,
            contrastText: telegramThemeColors.button_text_color || telegramText,
          },
          secondary: {
            main: telegramLink,
          },
          background: {
            default: telegramBg,
            paper: telegramPaper,
          },
          text: {
            primary: telegramText,
            secondary: telegramHint,
          },
        },
        typography: {
          fontFamily:
            '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
          h4: {
            fontWeight: 600,
            fontSize: "1.5rem",
          },
          h5: {
            fontWeight: 600,
            fontSize: "1.25rem",
          },
        },
        components: {
          MuiCssBaseline: {
            styleOverrides: {
              body: {
                backgroundColor: telegramBg,
                color: telegramText,
              },
            },
          },
          MuiPaper: {
            styleOverrides: {
              root: {
                backgroundColor: telegramPaper,
                borderRadius: 12,
                border: `1px solid ${
                  telegramThemeColors.hint_color || "#6c757d"
                }33`, // 33 = 20% opacity
              },
            },
          },
          MuiButton: {
            styleOverrides: {
              root: {
                textTransform: "none",
                borderRadius: 8,
                fontWeight: 500,
              },
              contained: {
                backgroundColor: telegramButton,
                color: telegramThemeColors.button_text_color || "#ffffff",
                boxShadow: "none",
                "&:hover": {
                  opacity: 0.9,
                  boxShadow: "none",
                },
              },
            },
          },
          MuiTextField: {
            styleOverrides: {
              root: {
                "& .MuiOutlinedInput-root": {
                  borderRadius: 8,
                  backgroundColor: `${
                    telegramThemeColors.hint_color || "#6c757d"
                  }0d`, // 0d = 5% opacity
                  "& fieldset": {
                    borderColor: `${
                      telegramThemeColors.hint_color || "#6c757d"
                    }3a`, // 3a = 23% opacity
                  },
                  "&:hover fieldset": {
                    borderColor: telegramButton,
                  },
                  "&.Mui-focused fieldset": {
                    borderColor: telegramButton,
                  },
                },
              },
            },
          },
        },
      });
    }
    return telegramTheme;
  }, [isInTelegram, telegramThemeColors]);

  return (
    <ThemeProvider theme={currentTheme}>
      <CssBaseline />
      {!isInTelegram && (
        <Button
          onClick={() =>
            window.open("https://t.me/tgfsprdbot/manager", "_blank")
          }
          variant="contained"
          sx={{
            position: "fixed",
            top: 16,
            right: 16,
            minWidth: "auto",
            borderRadius: "50px",
            px: 2,
            py: 1,
            bgcolor: "primary.main",
            color: "primary.contrastText",
            fontSize: "12px",
            fontWeight: "bold",
            boxShadow: 3,
            zIndex: 1000,
            "&:hover": {
              opacity: 0.9,
              transform: "translateY(-1px)",
            },
            transition: "all 0.2s ease-in-out",
          }}
          startIcon={<Telegram sx={{ fontSize: "16px !important" }} />}
        >
          Open in Telegram
        </Button>
      )}
      {isLoggedIn && webdavClient ? (
        <Container maxWidth="sm" sx={{ py: 2, minHeight: "100vh" }}>
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              mb: 2,
            }}
          >
            <Typography
              variant="h5"
              component="h1"
              sx={{ display: "flex", alignItems: "center", gap: 1 }}
            >
              <FolderOpen sx={{ color: "text.primary" }} />
              TGFS Explorer
            </Typography>
            <Button
              variant="outlined"
              color="secondary"
              onClick={handleLogout}
              size="small"
            >
              Logout
            </Button>
          </Box>
          <FileExplorer
            webdavClient={webdavClient}
            taskManagerClient={taskManagerClient ?? undefined}
          />
        </Container>
      ) : (
        <Container
          maxWidth="sm"
          sx={{
            py: 4,
            minHeight: "100vh",
            display: "flex",
            alignItems: "center",
          }}
        >
          <Paper elevation={3} sx={{ p: 4, width: "100%" }}>
            <Typography
              variant="h4"
              component="h1"
              gutterBottom
              sx={{ display: "flex", alignItems: "center", gap: 1 }}
            >
              <Login sx={{ color: "text.primary" }} />
              TGFS WebDAV Connection
            </Typography>

            <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
              Connect to your TGFS WebDAV server to browse and manage files
              stored on Telegram.
            </Typography>

            {error && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {error}
              </Alert>
            )}

            <Box
              component="form"
              sx={{ display: "flex", flexDirection: "column", gap: 2 }}
            >
              <TextField
                label="WebDAV URL"
                value={formData.webdavUrl}
                onChange={handleInputChange("webdavUrl")}
                placeholder="localhost or your-server.com"
                fullWidth
                required
                disabled={isLoading}
              />

              <FormControlLabel
                control={
                  <Switch
                    checked={formData.anonymous}
                    onChange={handleInputChange("anonymous")}
                    disabled={isLoading}
                  />
                }
                label={
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                    {formData.anonymous ? (
                      <WifiOff sx={{ color: "text.primary" }} />
                    ) : (
                      <Wifi sx={{ color: "text.primary" }} />
                    )}
                    Anonymous Login
                  </Box>
                }
              />

              {!formData.anonymous && (
                <>
                  <TextField
                    label="Username"
                    value={formData.username}
                    onChange={handleInputChange("username")}
                    fullWidth
                    required
                    disabled={isLoading}
                  />

                  <TextField
                    label="Password"
                    type="password"
                    value={formData.password}
                    onChange={handleInputChange("password")}
                    fullWidth
                    required
                    disabled={isLoading}
                  />
                </>
              )}

              <FormControlLabel
                control={
                  <Switch
                    checked={formData.enableManager}
                    onChange={handleInputChange("enableManager")}
                    disabled={isLoading}
                  />
                }
                label={
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                    <TaskAlt sx={{ color: "text.primary" }} />
                    Enable Task Manager
                  </Box>
                }
              />

              {formData.enableManager && (
                <>
                  <TextField
                    label="Task Manager Address"
                    value={formData.managerUrl}
                    onChange={handleInputChange("managerUrl")}
                    placeholder={formData.managerUrl}
                    fullWidth
                    disabled={isLoading}
                    helperText="URL for task manager server"
                  />
                </>
              )}

              <Button
                variant="contained"
                onClick={handleLogin}
                disabled={isLoading || !formData.webdavUrl}
                sx={{ mt: 2 }}
                startIcon={
                  isLoading ? <CircularProgress size={20} /> : <Login />
                }
              >
                {isLoading ? "Connecting..." : "Connect"}
              </Button>
            </Box>
          </Paper>
        </Container>
      )}
    </ThemeProvider>
  );
}
