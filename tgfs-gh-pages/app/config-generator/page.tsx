"use client";

import { Add, ContentCopy, Download, Refresh } from "@mui/icons-material";
import {
  Alert,
  AlertTitle,
  Box,
  Button,
  Card,
  CardContent,
  Checkbox,
  Container,
  FormControl,
  FormControlLabel,
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
import { ChannelField } from "./components/ChannelField";
import { ConfigTextField } from "./components/ConfigTextField";
import { FieldRow } from "./components/FieldRow";
import { FormSection } from "./components/FormSection";
import { UserField } from "./components/UserField";

interface ChannelConfig {
  id: string;
  name: string;
  type: "pinned_message" | "github_repo";
  github_repo?: {
    repo: string;
    commit: string;
    access_token: string;
  };
}

interface ConfigData {
  telegram: {
    api_id: string;
    api_hash: string;
    lib: "pyrogram" | "telethon";
    account: {
      session_file: string;
    };
    bot: {
      session_file: string;
      tokens: string[];
    };
    channels: ChannelConfig[];
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
    server: {
      host: string;
      port: number;
    };
  };
}

// Type-safe path mapping for updateConfig
type ConfigUpdatePaths = {
  "telegram.api_id": string;
  "telegram.api_hash": string;
  "telegram.lib": "pyrogram" | "telethon";
  "telegram.channels": ChannelConfig[];
  "telegram.bot.tokens": string[];
  "tgfs.users": { username: string; password: string }[];
  "tgfs.download.chunk_size_kb": number;
  "tgfs.jwt.secret": string;
  "tgfs.jwt.algorithm": string;
  "tgfs.jwt.life": number;
  "tgfs.server.host": string;
  "tgfs.server.port": number;
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
  const [withUserAccount, setWithUserAccount] = useState(false);

  const [config, setConfig] = useState<ConfigData>({
    telegram: {
      api_id: "",
      api_hash: "",
      lib: "pyrogram",
      account: {
        session_file: "account.session",
      },
      bot: {
        session_file: "bot.session",
        tokens: [""],
      },
      channels: [
        {
          id: "",
          name: "default",
          type: "pinned_message",
          github_repo: {
            repo: "",
            commit: "master",
            access_token: "",
          },
        },
      ],
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
      server: {
        host: "0.0.0.0",
        port: 1900,
      },
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
      } else if (path === "telegram.lib") {
        newConfig.telegram.lib = value as "pyrogram" | "telethon";
      } else if (path === "telegram.channels") {
        newConfig.telegram.channels = value as ChannelConfig[];
      } else if (path === "telegram.bot.tokens") {
        newConfig.telegram.bot.tokens = value as string[];
      } else if (path === "tgfs.users") {
        newConfig.tgfs.users = value as {
          username: string;
          password: string;
        }[];
      } else if (path === "tgfs.download.chunk_size_kb") {
        newConfig.tgfs.download.chunk_size_kb = value as number;
      } else if (path === "tgfs.jwt.secret") {
        newConfig.tgfs.jwt.secret = value as string;
      } else if (path === "tgfs.jwt.algorithm") {
        newConfig.tgfs.jwt.algorithm = value as string;
      } else if (path === "tgfs.jwt.life") {
        newConfig.tgfs.jwt.life = value as number;
      } else if (path === "tgfs.server.host") {
        newConfig.tgfs.server.host = value as string;
      } else if (path === "tgfs.server.port") {
        newConfig.tgfs.server.port = value as number;
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
    // Build metadata object from channels
    const metadata: {
      [channelId: string]: {
        name: string;
        type: "pinned_message" | "github_repo";
        github_repo?: {
          repo: string;
          commit: string;
          access_token: string;
        };
      };
    } = {};
    config.telegram.channels
      .filter((channel) => channel.id.trim() !== "")
      .forEach((channel) => {
        metadata[channel.id] = {
          name: channel.name,
          type: channel.type,
          ...(channel.type === "github_repo" && channel.github_repo
            ? { github_repo: channel.github_repo }
            : {}),
        };
      });

    const configForYaml = {
      telegram: {
        api_id: config.telegram.api_id,
        api_hash: config.telegram.api_hash,
        lib: config.telegram.lib,
        ...(withUserAccount ||
        Object.values(metadata).some(
          (channel) => channel.type === "pinned_message"
        )
          ? {
              account: {
                session_file: "account.session",
                used_to_upload: withUserAccount,
              },
            }
          : {}),
        bot: {
          session_file: config.telegram.bot.session_file,
          tokens: config.telegram.bot.tokens.filter(
            (token) => token.trim() !== ""
          ),
        },
        private_file_channel: config.telegram.channels
          .filter((channel) => channel.id.trim() !== "")
          .map((channel) => channel.id),
      },
      tgfs: {
        users: config.tgfs.users.reduce((acc, user) => {
          if (user.username.trim() !== "") {
            acc[user.username] = { password: user.password };
          }
          return acc;
        }, {} as { [key: string]: { password: string } }),
        download: config.tgfs.download,
        jwt: config.tgfs.jwt,
        metadata,
        server: config.tgfs.server,
      },
    };

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

  const addChannel = () => {
    const newChannels = [
      ...config.telegram.channels,
      {
        id: "",
        name: `channel-${config.telegram.channels.length + 1}`,
        type: "pinned_message" as const,
        github_repo: {
          repo: "",
          commit: "master",
          access_token: "",
        },
      },
    ];
    updateConfig("telegram.channels", newChannels);
  };

  const removeChannel = (index: number) => {
    const newChannels = config.telegram.channels.filter((_, i) => i !== index);
    updateConfig("telegram.channels", newChannels);
  };

  // Validation functions
  const isValidDirectoryName = (name: string): boolean => {
    // Valid directory name: no / \ : * ? " < > | and not . or ..
    const invalidChars = /[\/\\:*?"<>|]/;
    return (
      !invalidChars.test(name) &&
      name !== "." &&
      name !== ".." &&
      name.trim().length > 0
    );
  };

  const getChannelNameErrors = (index: number, name: string): string[] => {
    const errors: string[] = [];

    if (!name.trim()) {
      errors.push("Display name is required");
    } else {
      if (!isValidDirectoryName(name)) {
        errors.push('Invalid characters. Cannot contain: / \\ : * ? " < > |');
      }

      // Check for duplicates
      const duplicateIndex = config.telegram.channels.findIndex(
        (channel, i) =>
          i !== index &&
          channel.name.trim().toLowerCase() === name.trim().toLowerCase()
      );
      if (duplicateIndex !== -1) {
        errors.push("Display name must be unique across channels");
      }
    }

    return errors;
  };

  const updateChannel = (
    index: number,
    field: "id" | "name" | "type",
    value: string
  ) => {
    const newChannels = [...config.telegram.channels];
    if (field === "id" || field === "name") {
      newChannels[index][field] = value;
    } else if (field === "type") {
      newChannels[index][field] = value as "pinned_message" | "github_repo";
    }
    updateConfig("telegram.channels", newChannels);
  };

  const updateChannelGitHubRepo = (
    channelIndex: number,
    field: keyof NonNullable<ChannelConfig["github_repo"]>,
    value: string
  ) => {
    const newChannels = [...config.telegram.channels];
    if (!newChannels[channelIndex].github_repo) {
      newChannels[channelIndex].github_repo = {
        repo: "",
        commit: "master",
        access_token: "",
      };
    }
    newChannels[channelIndex].github_repo![field] = value;
    updateConfig("telegram.channels", newChannels);
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
            <FormSection title="Telegram" showDivider={false}>
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
              <FieldRow justifyContent="space-between">
                <ConfigTextField
                  label="API ID"
                  value={config.telegram.api_id}
                  onChange={(e) =>
                    updateConfig("telegram.api_id", e.target.value)
                  }
                  style={{ flex: 1 }}
                  required
                />
                <ConfigTextField
                  label="API Hash"
                  value={config.telegram.api_hash}
                  onChange={(e) =>
                    updateConfig("telegram.api_hash", e.target.value)
                  }
                  style={{ flex: 1 }}
                  required
                />
                <FormControl size="small" sx={{ minWidth: 200 }}>
                  <InputLabel>Telegram Library</InputLabel>
                  <Select
                    value={config.telegram.lib}
                    label="Telegram Library"
                    onChange={(e) =>
                      updateConfig(
                        "telegram.lib",
                        e.target.value as "pyrogram" | "telethon"
                      )
                    }
                  >
                    <MenuItem value="pyrogram">Pyrogram</MenuItem>
                    <MenuItem value="telethon">Telethon</MenuItem>
                  </Select>
                </FormControl>
              </FieldRow>

              <Box>
                <Typography variant="h6" sx={{ mb: 2 }}>
                  Private File Channels & Metadata
                </Typography>
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{ mb: 2 }}
                >
                  Configure one or more private channels to store files. Each
                  channel needs both a channel ID and metadata configuration to
                  maintain the directory structure.
                </Typography>
                {config.telegram.channels.map((channel, index) => (
                  <ChannelField
                    key={index}
                    index={index}
                    channel={channel}
                    onUpdate={(field, value) =>
                      updateChannel(index, field, value)
                    }
                    onUpdateGitHubRepo={(field, value) =>
                      updateChannelGitHubRepo(index, field, value)
                    }
                    onDelete={
                      config.telegram.channels.length > 1
                        ? () => removeChannel(index)
                        : undefined
                    }
                    canDelete={config.telegram.channels.length > 1}
                    nameErrors={getChannelNameErrors(index, channel.name)}
                  />
                ))}
                <Button
                  startIcon={<Add />}
                  onClick={addChannel}
                  variant="outlined"
                  size="small"
                  sx={{ mt: 1 }}
                >
                  Add Another Channel
                </Button>
              </Box>

              <FormControlLabel
                label="Use user account to upload files (No benefit unless you are a premium user)"
                control={
                  <Checkbox
                    checked={withUserAccount}
                    onChange={(e) => {
                      setWithUserAccount(e.target.checked);
                    }}
                  />
                }
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
              <Typography variant="h6" sx={{ mt: 2, mb: 1 }}>
                Server
              </Typography>
              <FieldRow>
                <ConfigTextField
                  label="Host"
                  value={config.tgfs.server.host}
                  onChange={(e) =>
                    updateConfig("tgfs.server.host", e.target.value)
                  }
                  width={200}
                />
                <ConfigTextField
                  label="Port"
                  type="number"
                  value={config.tgfs.server.port}
                  onChange={(e) =>
                    updateConfig("tgfs.server.port", parseInt(e.target.value))
                  }
                  width={120}
                />
              </FieldRow>
              <Typography variant="body2" color="text.secondary">
                WebDAV server will be at{" "}
                <code>
                  http://{config.tgfs.server.host}:{config.tgfs.server.port}
                  /webdav
                </code>
              </Typography>
              <Typography variant="body2" color="text.secondary">
                TGFS server will be at{" "}
                <code>
                  http://{config.tgfs.server.host}:{config.tgfs.server.port}
                </code>{" "}
                {"("}Used in the{" "}
                <a href="https://theodorekrypton.github.io/tgfs/telegram-mini-app/">
                  <u>Telegram Mini App</u>
                </a>
                {")"}.
              </Typography>
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
