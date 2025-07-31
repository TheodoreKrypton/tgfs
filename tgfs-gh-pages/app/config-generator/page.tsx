"use client";

import { Add, ContentCopy, Download, Refresh } from "@mui/icons-material";
import {
  Alert,
  AlertTitle,
  Box,
  Button,
  Card,
  CardContent,
  Container,
  FormControl,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Typography,
} from "@mui/material";
import yaml from "js-yaml";
import { useCallback, useEffect, useState } from "react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import { BotTokenField } from "./components/BotTokenField";
import { ConfigTextField } from "./components/ConfigTextField";
import { FieldRow } from "./components/FieldRow";
import { FormSection } from "./components/FormSection";
import { UserField } from "./components/UserField";

interface ConfigData {
  telegram: {
    api_id: string;
    api_hash: string;
    account: {
      session_file: string;
    };
    bot: {
      session_file: string;
      tokens: string[];
    };
    private_file_channel: string;
    public_file_channel: number;
  };
  tgfs: {
    users: {
      username: string;
      password: string;
    }[];
    download: {
      chunk_size_kb: number;
    };
    jwt: {
      secret: string;
      algorithm: string;
      life: number;
    };
    metadata: {
      type: "pinned_message" | "github_repo";
      github_repo?: {
        repo: string;
        commit: string;
        access_token: string;
      };
    };
  };
  webdav: {
    host: string;
    port: number;
    path: string;
  };
  manager?: {
    host: string;
    port: number;
  };
}

// Type-safe path mapping for updateConfig
type ConfigUpdatePaths = {
  "telegram.api_id": string;
  "telegram.api_hash": string;
  "telegram.private_file_channel": string;
  "telegram.bot.tokens": string[];
  "tgfs.users": { username: string; password: string }[];
  "tgfs.download.chunk_size_kb": number;
  "webdav.host": string;
  "webdav.port": number;
  "webdav.path": string;
  "tgfs.jwt.secret": string;
  "tgfs.jwt.algorithm": string;
  "tgfs.jwt.life": number;
  "tgfs.metadata.type": "pinned_message" | "github_repo";
  "tgfs.metadata.github_repo.repo": string;
  "tgfs.metadata.github_repo.commit": string;
  "tgfs.metadata.github_repo.access_token": string;
  "manager.host": string;
  "manager.port": number;
};

const generateRandomSecret = (): string => {
  const chars =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*()_+-=[]{}|;:,.<>?";
  let result = "";
  for (let i = 0; i < 64; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return result;
};

export default function ConfigGenerator() {
  const [config, setConfig] = useState<ConfigData>({
    telegram: {
      api_id: "",
      api_hash: "",
      account: {
        session_file: "account.session",
      },
      bot: {
        session_file: "bot.session",
        tokens: [""],
      },
      private_file_channel: "",
      public_file_channel: 0,
    },
    tgfs: {
      users: [
        {
          username: "user",
          password: "password",
        },
      ],
      download: {
        chunk_size_kb: 1024,
      },
      jwt: {
        secret: "",
        algorithm: "HS256",
        life: 604800,
      },
      metadata: {
        type: "pinned_message",
        github_repo: {
          repo: "",
          commit: "master",
          access_token: "",
        },
      },
    },
    webdav: {
      host: "0.0.0.0",
      port: 1900,
      path: "/",
    },
  });

  const updateConfig = useCallback(
    <K extends keyof ConfigUpdatePaths>(
      path: K,
      value: ConfigUpdatePaths[K]
    ): void => {
      const newConfig = { ...config };

      if (path === "telegram.api_id") {
        newConfig.telegram.api_id = value as string;
      } else if (path === "telegram.api_hash") {
        newConfig.telegram.api_hash = value as string;
      } else if (path === "telegram.private_file_channel") {
        newConfig.telegram.private_file_channel = value as string;
      } else if (path === "telegram.bot.tokens") {
        newConfig.telegram.bot.tokens = value as string[];
      } else if (path === "tgfs.users") {
        newConfig.tgfs.users = value as {
          username: string;
          password: string;
        }[];
      } else if (path === "tgfs.download.chunk_size_kb") {
        newConfig.tgfs.download.chunk_size_kb = value as number;
      } else if (path === "webdav.host") {
        newConfig.webdav.host = value as string;
      } else if (path === "webdav.port") {
        newConfig.webdav.port = value as number;
      } else if (path === "webdav.path") {
        newConfig.webdav.path = value as string;
      } else if (path === "tgfs.jwt.secret") {
        newConfig.tgfs.jwt.secret = value as string;
      } else if (path === "tgfs.jwt.algorithm") {
        newConfig.tgfs.jwt.algorithm = value as string;
      } else if (path === "tgfs.jwt.life") {
        newConfig.tgfs.jwt.life = value as number;
      } else if (path === "tgfs.metadata.type") {
        newConfig.tgfs.metadata.type = value as
          | "pinned_message"
          | "github_repo";
      } else if (path === "tgfs.metadata.github_repo.repo") {
        if (!newConfig.tgfs.metadata.github_repo) {
          newConfig.tgfs.metadata.github_repo = {
            repo: "",
            commit: "master",
            access_token: "",
          };
        }
        newConfig.tgfs.metadata.github_repo.repo = value as string;
      } else if (path === "tgfs.metadata.github_repo.commit") {
        if (!newConfig.tgfs.metadata.github_repo) {
          newConfig.tgfs.metadata.github_repo = {
            repo: "",
            commit: "master",
            access_token: "",
          };
        }
        newConfig.tgfs.metadata.github_repo.commit = value as string;
      } else if (path === "tgfs.metadata.github_repo.access_token") {
        if (!newConfig.tgfs.metadata.github_repo) {
          newConfig.tgfs.metadata.github_repo = {
            repo: "",
            commit: "master",
            access_token: "",
          };
        }
        newConfig.tgfs.metadata.github_repo.access_token = value as string;
      } else if (path === "manager.host") {
        if (!newConfig.manager) {
          newConfig.manager = { host: "0.0.0.0", port: 1901 };
        }
        newConfig.manager.host = value as string;
      } else if (path === "manager.port") {
        if (!newConfig.manager) {
          newConfig.manager = { host: "0.0.0.0", port: 1901 };
        }
        newConfig.manager.port = value as number;
      }

      setConfig(newConfig);
    },
    [config]
  );

  // Generate JWT secret on client side only to avoid hydration mismatch
  useEffect(() => {
    if (config.tgfs.jwt.secret === "") {
      updateConfig("tgfs.jwt.secret", generateRandomSecret());
    }
  }, [config.tgfs.jwt.secret, updateConfig]);

  const addBotToken = () => {
    const newTokens = [...config.telegram.bot.tokens, ""];
    updateConfig("telegram.bot.tokens", newTokens);
  };

  const removeBotToken = (index: number) => {
    const newTokens = config.telegram.bot.tokens.filter((_, i) => i !== index);
    updateConfig("telegram.bot.tokens", newTokens);
  };

  const updateBotToken = (index: number, value: string) => {
    const newTokens = [...config.telegram.bot.tokens];
    newTokens[index] = value;
    updateConfig("telegram.bot.tokens", newTokens);
  };

  const generateYaml = () => {
    // Convert users array to object format for YAML output
    const metadata =
      config.tgfs.metadata.type === "github_repo"
        ? {
            type: config.tgfs.metadata.type,
            github_repo: config.tgfs.metadata.github_repo,
          }
        : { type: config.tgfs.metadata.type };

    const configForYaml = {
      ...config,
      tgfs: {
        ...config.tgfs,
        users: config.tgfs.users.reduce((acc, user) => {
          acc[user.username] = { password: user.password };
          return acc;
        }, {} as { [key: string]: { password: string } }),
        metadata,
      },
    };

    // Only include manager if host and port are provided
    if (config.manager?.host && config.manager?.port) {
      configForYaml.manager = config.manager;
    }
    return yaml.dump(configForYaml, { indent: 2 });
  };

  const downloadConfig = () => {
    const yamlContent = generateYaml();
    const blob = new Blob([yamlContent], { type: "text/yaml" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "config.yaml";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const copyToClipboard = () => {
    const yamlContent = generateYaml();
    navigator.clipboard.writeText(yamlContent);
  };

  const regenerateJwtSecret = () => {
    updateConfig("tgfs.jwt.secret", generateRandomSecret());
  };

  const addUser = () => {
    const newUsers = [...config.tgfs.users, { username: "", password: "" }];
    updateConfig("tgfs.users", newUsers);
  };

  const removeUser = (index: number) => {
    const newUsers = config.tgfs.users.filter((_, i) => i !== index);
    updateConfig("tgfs.users", newUsers);
  };

  const updateUser = (
    index: number,
    field: "username" | "password",
    value: string
  ) => {
    const newUsers = [...config.tgfs.users];
    newUsers[index][field] = value;
    updateConfig("tgfs.users", newUsers);
  };

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Typography variant="h3" component="h1" gutterBottom align="center">
        TGFS Config Generator
      </Typography>

      <Typography
        variant="h6"
        color="text.secondary"
        align="center"
        sx={{ mb: 4 }}
      >
        Generate your TGFS configuration file with this interactive form
      </Typography>

      <Alert severity="warning" sx={{ mb: 3 }}>
        <AlertTitle>Important</AlertTitle>
        Keep your API credentials and bot tokens secure. Never share them
        publicly.
      </Alert>

      <Box
        sx={{
          display: "flex",
          gap: 3,
          flexDirection: { xs: "column", md: "row" },
        }}
      >
        <Box sx={{ flex: 1 }}>
          <Paper sx={{ p: 3 }}>
            <FormSection title="Telegram Configuration" showDivider={false}>
              <Box
                sx={{ display: "flex", alignItems: "center", gap: 2, mb: 2 }}
              >
                <Typography variant="h6">API Credentials</Typography>
                <Button
                  variant="outlined"
                  size="small"
                  component="a"
                  href="https://my.telegram.org/apps"
                  target="_blank"
                  rel="noopener noreferrer"
                  sx={{ textTransform: "none" }}
                >
                  Get API Keys
                </Button>
              </Box>
              <FieldRow>
                <ConfigTextField
                  label="API ID"
                  value={config.telegram.api_id}
                  onChange={(e) =>
                    updateConfig("telegram.api_id", e.target.value)
                  }
                  required
                />
                <ConfigTextField
                  label="API Hash"
                  value={config.telegram.api_hash}
                  onChange={(e) =>
                    updateConfig("telegram.api_hash", e.target.value)
                  }
                  required
                />
              </FieldRow>

              <ConfigTextField
                label="Private File Channel ID"
                value={config.telegram.private_file_channel}
                onChange={(e) =>
                  updateConfig("telegram.private_file_channel", e.target.value)
                }
                helperText="Channel ID (numeric, e.g., 1234567)"
                required
                width={400}
              />

              <Box>
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    gap: 2,
                    mt: 2,
                    mb: 2,
                  }}
                >
                  <Typography variant="h6">Bot Tokens</Typography>
                  <Button
                    variant="outlined"
                    size="small"
                    component="a"
                    href="https://t.me/botfather"
                    target="_blank"
                    rel="noopener noreferrer"
                    sx={{ textTransform: "none" }}
                  >
                    @BotFather
                  </Button>
                </Box>
                {config.telegram.bot.tokens.map((token, index) => (
                  <BotTokenField
                    key={index}
                    index={index}
                    value={token}
                    onChange={(value) => updateBotToken(index, value)}
                    onDelete={
                      index > 0 ? () => removeBotToken(index) : undefined
                    }
                  />
                ))}
                <Button
                  startIcon={<Add />}
                  onClick={addBotToken}
                  variant="outlined"
                  size="small"
                  sx={{ mt: 1 }}
                >
                  Add Another Bot Token
                </Button>
              </Box>
            </FormSection>

            <FormSection title="TGFS">
              <Box>
                <Typography variant="h6" sx={{ mb: 2 }}>
                  Users
                </Typography>
                {config.tgfs.users.map((user, index) => (
                  <UserField
                    key={index}
                    username={user.username}
                    password={user.password}
                    onUsernameChange={(username) =>
                      updateUser(index, "username", username)
                    }
                    onPasswordChange={(password) =>
                      updateUser(index, "password", password)
                    }
                    onDelete={index > 0 ? () => removeUser(index) : undefined}
                    canDelete={index > 0}
                  />
                ))}
                <Button
                  startIcon={<Add />}
                  onClick={addUser}
                  variant="outlined"
                  size="small"
                  sx={{ mt: 1, width: "fit-content" }}
                >
                  Add Another User
                </Button>
              </Box>

              <Typography variant="h6" sx={{ mt: 2, mb: 1 }}>
                JWT
              </Typography>

              <Box sx={{ display: "flex", gap: 1, mb: 2 }}>
                <ConfigTextField
                  label="JWT Secret"
                  value={config.tgfs.jwt.secret}
                  onChange={(e) =>
                    updateConfig("tgfs.jwt.secret", e.target.value)
                  }
                  sx={{ flex: 1 }}
                />
                <Button
                  variant="outlined"
                  size="small"
                  startIcon={<Refresh />}
                  onClick={regenerateJwtSecret}
                  sx={{ minWidth: "120px" }}
                >
                  Regenerate
                </Button>
              </Box>

              <Typography variant="h6" sx={{ mt: 2, mb: 2 }}>
                Metadata
              </Typography>

              <FormControl size="small" sx={{ mb: 2 }}>
                <InputLabel>Metadata Type</InputLabel>
                <Select
                  value={config.tgfs.metadata.type}
                  label="Metadata Type"
                  onChange={(e) =>
                    updateConfig(
                      "tgfs.metadata.type",
                      e.target.value as "pinned_message" | "github_repo"
                    )
                  }
                >
                  <MenuItem value="pinned_message">Pinned Message</MenuItem>
                  <MenuItem value="github_repo">GitHub Repository</MenuItem>
                </Select>
              </FormControl>

              {config.tgfs.metadata.type === "github_repo" && (
                <Box sx={{ pl: 2, borderLeft: "3px solid #e0e0e0", ml: 1 }}>
                  <Typography
                    variant="subtitle1"
                    sx={{ mb: 2, fontWeight: 500 }}
                  >
                    GitHub Repository Settings
                  </Typography>

                  <ConfigTextField
                    label="Repository"
                    value={config.tgfs.metadata.github_repo?.repo || ""}
                    onChange={(e) =>
                      updateConfig(
                        "tgfs.metadata.github_repo.repo",
                        e.target.value
                      )
                    }
                    helperText="Format: username/repository-name"
                    required
                    sx={{ mb: 2 }}
                  />

                  <FieldRow>
                    <ConfigTextField
                      label="Commit/Branch"
                      value={
                        config.tgfs.metadata.github_repo?.commit || "master"
                      }
                      onChange={(e) =>
                        updateConfig(
                          "tgfs.metadata.github_repo.commit",
                          e.target.value
                        )
                      }
                      width={200}
                    />
                    <ConfigTextField
                      label="Access Token"
                      value={
                        config.tgfs.metadata.github_repo?.access_token || ""
                      }
                      onChange={(e) =>
                        updateConfig(
                          "tgfs.metadata.github_repo.access_token",
                          e.target.value
                        )
                      }
                      required
                      sx={{ flex: 1 }}
                    />
                    <Box
                      sx={{
                        display: "flex",
                        alignItems: "center",
                        gap: 2,
                        mb: 2,
                      }}
                    >
                      <Button
                        variant="outlined"
                        component="a"
                        href="https://github.com/settings/personal-access-tokens/new"
                        target="_blank"
                        rel="noopener noreferrer"
                        sx={{ textTransform: "none" }}
                      >
                        Get Access Token
                      </Button>
                    </Box>
                  </FieldRow>
                </Box>
              )}
            </FormSection>

            <FormSection title="WebDAV Server">
              <FieldRow>
                <ConfigTextField
                  label="Host"
                  value={config.webdav.host}
                  onChange={(e) => updateConfig("webdav.host", e.target.value)}
                  width={200}
                />
                <ConfigTextField
                  label="Port"
                  type="number"
                  value={config.webdav.port}
                  onChange={(e) =>
                    updateConfig("webdav.port", parseInt(e.target.value))
                  }
                  width={120}
                />
                <ConfigTextField
                  label="Path"
                  value={config.webdav.path}
                  onChange={(e) => updateConfig("webdav.path", e.target.value)}
                  width={120}
                />
              </FieldRow>
            </FormSection>

            <FormSection title="Task Manager Server (Optional)">
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Configure the task manager server to track upload/download
                progress in real-time.
              </Typography>
              <FieldRow>
                <ConfigTextField
                  label="Host"
                  value={config.manager?.host || "0.0.0.0"}
                  onChange={(e) => updateConfig("manager.host", e.target.value)}
                  width={200}
                />
                <ConfigTextField
                  label="Port"
                  type="number"
                  value={config.manager?.port || 1901}
                  onChange={(e) =>
                    updateConfig("manager.port", parseInt(e.target.value))
                  }
                  width={120}
                />
              </FieldRow>
            </FormSection>
          </Paper>
        </Box>

        <Box sx={{ width: { xs: "100%", md: "400px" }, flexShrink: 0 }}>
          <Paper sx={{ p: 3, position: "sticky", top: 24 }}>
            <Typography variant="h6" gutterBottom>
              Generated Configuration
            </Typography>

            <Box sx={{ mb: 2 }}>
              <Button
                fullWidth
                variant="contained"
                startIcon={<Download />}
                onClick={downloadConfig}
                sx={{ mb: 1 }}
              >
                Download config.yaml
              </Button>
              <Button
                fullWidth
                variant="outlined"
                startIcon={<ContentCopy />}
                onClick={copyToClipboard}
              >
                Copy to Clipboard
              </Button>
            </Box>

            <Card variant="outlined">
              <CardContent sx={{ p: 0 }}>
                <SyntaxHighlighter
                  language="yaml"
                  style={vscDarkPlus}
                  customStyle={{
                    fontSize: "0.75rem",
                    margin: 0,
                    maxHeight: "400px",
                    overflow: "auto",
                  }}
                >
                  {generateYaml()}
                </SyntaxHighlighter>
              </CardContent>
            </Card>
          </Paper>
        </Box>
      </Box>
    </Container>
  );
}
