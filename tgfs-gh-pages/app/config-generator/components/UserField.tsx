import { Box, IconButton } from '@mui/material';
import { Delete } from '@mui/icons-material';
import { ConfigTextField } from './ConfigTextField';

interface UserFieldProps {
  username: string;
  password: string;
  onUsernameChange: (username: string) => void;
  onPasswordChange: (password: string) => void;
  onDelete?: () => void;
  canDelete: boolean;
}

export function UserField({ 
  username,
  password,
  onUsernameChange,
  onPasswordChange,
  onDelete,
  canDelete
}: UserFieldProps) {
  return (
    <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1, mb: 1 }}>
      <ConfigTextField
        label="Username"
        value={username}
        onChange={(e) => onUsernameChange(e.target.value)}
        width={200}
        required
      />
      <ConfigTextField
        label="Password"
        value={password}
        onChange={(e) => onPasswordChange(e.target.value)}
        width={200}
        required
      />
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
  );
}