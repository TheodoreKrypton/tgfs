import { IconButton, Tooltip } from '@mui/material';
import { OpenInNew } from '@mui/icons-material';

interface ExternalLinkIconProps {
  url: string;
  tooltip?: string;
}

export function ExternalLinkIcon({ url, tooltip = 'Open external link' }: ExternalLinkIconProps) {
  return (
    <Tooltip title={tooltip}>
      <IconButton 
        size="small" 
        onClick={() => window.open(url, '_blank')}
        sx={{ alignSelf: 'flex-start', mt: 1 }}
      >
        <OpenInNew fontSize="small" />
      </IconButton>
    </Tooltip>
  );
}