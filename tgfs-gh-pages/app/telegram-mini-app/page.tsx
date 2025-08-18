"use client";

import {
  FolderOpen,
  Login,
  Telegram,
  Wifi,
  WifiOff,
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
import {
  init,
  isTMA,
  miniApp,
  retrieveLaunchParams,
  viewport,
  cloudStorage,
} from "@telegram-apps/sdk";
import type { ThemeParams } from "@telegram-apps/types";
import Cookies from "js-cookie";
import Link from "next/link";
import React, { useEffect, useState } from "react";
import errors from "./error";
import FileExplorer from "./file-explorer";
import ManagerClient from "./manager-client";
import { telegramTheme } from "./telegram-theme";
import WebDAVClient from "./webdav-client";

interface LoginFormData {
  tgfsUrl: string;
  username: string;
  password: string;
  anonymous: boolean;
}

type SavedInfo = {
  tgfsUrl: string;
  username: string;
};

const SAVED_INFO_KEY = "saved_info";
const JWT_TOKEN_KEY = "jwt_token";

export default function TelegramMiniApp() {
  // State management
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [webdavClient, setWebdavClient] = useState<WebDAVClient | null>(null);
  const [managerClient, setManagerClient] = useState<ManagerClient | null>(
    null
  );
  const [isInTelegram, setIsInTelegram] = useState(false);
  const [telegramThemeColors, setTelegramThemeColors] =
    useState<ThemeParams | null>(null);
  const [formData, setFormData] = useState<LoginFormData>({
    tgfsUrl: "",
    username: "",
    password: "",
    anonymous: false,
  });

  const handleError = (message: string) => {
    setError(message);
  };

  const retrieveToken = React.useCallback(async (): Promise<string> => {
    const retrievedString = isInTelegram
      ? await cloudStorage.getItem(JWT_TOKEN_KEY)
      : Cookies.get("jwt_token");
    return retrievedString ?? "";
  }, [isInTelegram]);

  const retrieveSavedInfo = React.useCallback(async (): Promise<SavedInfo> => {
    const retrievedString = isInTelegram
      ? await cloudStorage.getItem(SAVED_INFO_KEY)
      : localStorage.getItem(SAVED_INFO_KEY);
    return retrievedString
      ? (JSON.parse(retrievedString) as SavedInfo)
      : {
          tgfsUrl: "",
          username: "",
        };
  }, [isInTelegram]);

  const clearToken = React.useCallback(async () => {
    if (isInTelegram) {
      try {
        await cloudStorage.deleteItem(JWT_TOKEN_KEY);
      } catch {}
    }
    // Always clear cookies as fallback
    Cookies.remove("jwt_token");
  }, [isInTelegram]);

  const saveToken = React.useCallback(
    async (token: string) => {
      if (isInTelegram) {
        await cloudStorage.setItem(JWT_TOKEN_KEY, token);
      } else {
        Cookies.set("jwt_token", token);
      }
    },
    [isInTelegram]
  );

  const saveSavedInfo = React.useCallback(
    async (savedInfo: SavedInfo) => {
      if (isInTelegram) {
        await cloudStorage.setItem(SAVED_INFO_KEY, JSON.stringify(savedInfo));
      } else {
        localStorage.setItem(SAVED_INFO_KEY, JSON.stringify(savedInfo));
      }
    },
    [isInTelegram]
  );

  // Initialize app on mount
  useEffect(() => {
    const initializeApp = async () => {
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
        }
      } catch {
        setIsInTelegram(false);
      }
    };

    initializeApp();
  }, [retrieveToken]);

  useEffect(() => {
    const restoreSession = async () => {
      // Restore session from storage (cloud storage for Telegram, cookies for browser)
      const token = await retrieveToken();
      const savedInfo = await retrieveSavedInfo();

      setFormData((prev) => ({
        ...prev,
        tgfsUrl: savedInfo.tgfsUrl ?? "",
        username: savedInfo.username ?? "",
      }));

      if (token && savedInfo.tgfsUrl) {
        const client = new WebDAVClient(
          `${savedInfo.tgfsUrl}/webdav`,
          token,
          handleError
        );
        setWebdavClient(client);

        const managerClient = new ManagerClient(
          `${savedInfo.tgfsUrl}/api`,
          token
        );
        setManagerClient(managerClient);

        setIsLoggedIn(true);
      }
    };

    restoreSession();
  }, [retrieveToken, retrieveSavedInfo]);

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
      const response = await fetch(`${formData.tgfsUrl}/login`, {
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
        throw new errors.CatchableError(await response.text());
      }

      const data = await response.json();
      const token = data.token;

      // Store JWT token in cloud storage (Telegram) or cookies (browser)
      await saveToken(token);

      await saveSavedInfo({
        tgfsUrl: formData.tgfsUrl,
        username: formData.username,
      });

      // Create WebDAV client with JWT token
      const client = new WebDAVClient(
        `${formData.tgfsUrl}/webdav`,
        token,
        handleError
      );
      await client.connect();
      setWebdavClient(client);

      const managerClient = new ManagerClient(`${formData.tgfsUrl}/api`, token);
      setManagerClient(managerClient);

      setIsLoggedIn(true);
    } catch (err) {
      if (err instanceof errors.CatchableError) {
        setError(err.message);
      } else {
        let potentialReason = "";
        if (
          window.location.protocol === "https:" &&
          !formData.tgfsUrl.startsWith("https://")
        ) {
          potentialReason =
            "URL must start with https:// when using secure connections.";
        }
        setError(
          `The URL is not a TGFS server, or is not reachable. ${potentialReason}`
        );
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleLogout = React.useCallback(async () => {
    // Clear session data from cloud storage (Telegram) or cookies (browser)
    await clearToken();

    setIsLoggedIn(false);
    setWebdavClient(null);
    setManagerClient(null);
    setError(null);
  }, [clearToken]);

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
          <Link
            href="https://t.me/tgfsprdbot/manager"
            target="_blank"
            rel="noopener noreferrer"
            style={{ color: "inherit", textDecoration: "none" }}
          >
            Open in Telegram
          </Link>
        </Button>
      )}
      {isLoggedIn && webdavClient && managerClient ? (
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
              size="small"
              onClick={handleLogout}
            >
              Logout
            </Button>
          </Box>
          <FileExplorer
            webdavClient={webdavClient}
            managerClient={managerClient}
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
              mb={3}
            >
              <Login sx={{ color: "text.primary" }} />
              Login to TGFS
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
                label="TGFS Server URL (without /webdav suffix)"
                value={formData.tgfsUrl}
                onChange={handleInputChange("tgfsUrl")}
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

              <Button
                variant="contained"
                onClick={handleLogin}
                disabled={isLoading || !formData.tgfsUrl}
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
