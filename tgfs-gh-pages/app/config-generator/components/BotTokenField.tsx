import { Box, IconButton } from '@mui/material';
import { Delete } from '@mui/icons-material';
import { ConfigTextField } from './ConfigTextField';

interface BotTokenFieldProps {
  index: number;
  value: string;
  onChange: (value: string) => void;
  onDelete?: () => void;
}

export function BotTokenField({ 
  index, 
  value, 
  onChange, 
  onDelete
}: BotTokenFieldProps) {
  return (
    <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1, mb: 1 }}>
      <ConfigTextField
        label={`Bot Token ${index + 1}`}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        helperText=""
        required={index === 0}
        width={400}
      />
      {index > 0 && onDelete && (
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