import { Delete } from "@mui/icons-material";
import {
  Box,
  Button,
  FormControl,
  IconButton,
  InputLabel,
  MenuItem,
  Select,
  Typography,
} from "@mui/material";
import { ConfigTextField } from "./ConfigTextField";

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

interface ChannelFieldProps {
  index: number;
  channel: ChannelConfig;
  onUpdate: (field: "id" | "name" | "type", value: string) => void;
  onUpdateGitHubRepo: (
    field: keyof NonNullable<ChannelConfig["github_repo"]>,
    value: string
  ) => void;
  onDelete?: () => void;
  canDelete: boolean;
  nameErrors?: string[];
}

export function ChannelField({
  channel,
  onUpdate,
  onUpdateGitHubRepo,
  onDelete,
  canDelete,
  nameErrors = [],
}: ChannelFieldProps) {
  return (
    <Box sx={{ mb: 2 }}>
      {/* Channel ID Row */}
      <Box sx={{ display: "flex", alignItems: "flex-start", gap: 1, mb: 2 }}>
        <ConfigTextField
          label={`Channel ID`}
          value={channel.id}
          onChange={(e) => onUpdate("id", e.target.value)}
          required
          style={{ flex: 1 }}
        />
        <ConfigTextField
          label="Display Name"
          value={channel.name}
          onChange={(e) => onUpdate("name", e.target.value)}
          required
          error={nameErrors.length > 0}
          helperText={
            nameErrors.length > 0
              ? nameErrors.join("; ")
              : "Valid directory name for metadata"
          }
          style={{ flex: 1 }}
        />
        <FormControl size="small" sx={{ minWidth: 200 }}>
          <InputLabel>Metadata Type</InputLabel>
          <Select
            value={channel.type}
            label="Metadata Type"
            onChange={(e) =>
              onUpdate(
                "type",
                e.target.value as "pinned_message" | "github_repo"
              )
            }
          >
            <MenuItem value="pinned_message">Pinned Message</MenuItem>
            <MenuItem value="github_repo">GitHub Repository</MenuItem>
          </Select>
        </FormControl>
        {canDelete && onDelete && (
          <IconButton
            color="error"
            onClick={onDelete}
            sx={{ mt: 0.5 }}
            size="small"
          >
            <Delete />
          </IconButton>
        )}
      </Box>

      {/* Metadata Name and Type Row */}
      <Box
        sx={{ display: "flex", alignItems: "flex-start", gap: 1, mb: 1 }}
      ></Box>

      <Typography variant="body2" color="text.secondary" sx={{ mb: 2, pl: 2 }}>
        {channel.type === "pinned_message"
          ? "The metadata will be maintained in a json file pinned in the file channel. Every directory operation reuploads and updates the pinned file."
          : "The metadata will be maintained by a GitHub repository configured in the following github_repo section. Every directory operation is mapped to the github repository."}
      </Typography>
      {channel.type === "pinned_message" && (
        <Typography
          variant="body2"
          color="text.secondary"
          sx={{ mb: 2, pl: 2 }}
        >
          ⚠️ NEVER delete the pinned file AND NEVER manually pin any message.
        </Typography>
      )}
      {channel.type === "github_repo" && (
        <Box sx={{ mb: 2, pl: 2 }}>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            <b>Merits:</b>
          </Typography>
          <Box
            component="ul"
            sx={{
              margin: 0,
              paddingLeft: 2,
              listStyleType: "disc",
              listStylePosition: "inside",
              color: "text.secondary",
              fontSize: "0.875rem",
            }}
          >
            <li>
              Directory operations are faster (possibly?) because the metadata
              is not re-uploaded every time.
            </li>
            <li>
              The metadata is versioned naturally, so rollback is possible.
            </li>
            <li>
              Multiple clients can access / mutate the same metadata without
              conflict.
            </li>
          </Box>
        </Box>
      )}

      {/* GitHub Repo Settings (only if github_repo type) */}
      {channel.type === "github_repo" && (
        <>
          <Box
            sx={{ display: "flex", alignItems: "flex-start", gap: 1, mb: 1 }}
          >
            <ConfigTextField
              label="Repository"
              value={channel.github_repo?.repo || ""}
              onChange={(e) => onUpdateGitHubRepo("repo", e.target.value)}
              helperText="Format: username/repository-name"
              required
              style={{ flex: 1 }}
            />
            <ConfigTextField
              label="Commit/Branch"
              value={channel.github_repo?.commit || "master"}
              onChange={(e) => onUpdateGitHubRepo("commit", e.target.value)}
              width={200}
            />
          </Box>
          <Box
            sx={{ display: "flex", alignItems: "flex-start", gap: 1, mb: 1 }}
          >
            <ConfigTextField
              label="Access Token"
              value={channel.github_repo?.access_token || ""}
              onChange={(e) =>
                onUpdateGitHubRepo("access_token", e.target.value)
              }
              type="password"
              required
              style={{ flex: 1 }}
            />
            <Button
              variant="outlined"
              component="a"
              size="large"
              href="https://github.com/settings/personal-access-tokens/new"
              target="_blank"
              rel="noopener noreferrer"
              sx={{ textTransform: "none" }}
            >
              Get Token
            </Button>
          </Box>
        </>
      )}
    </Box>
  );
}
