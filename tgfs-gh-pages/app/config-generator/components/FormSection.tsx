import { Typography, Divider, Box } from '@mui/material';
import { ReactNode } from 'react';

interface FormSectionProps {
  title: string;
  children: ReactNode;
  showDivider?: boolean;
}

export function FormSection({ title, children, showDivider = true }: FormSectionProps) {
  return (
    <>
      {showDivider && <Divider sx={{ my: 3 }} />}
      <Typography variant="h5" gutterBottom>
        {title}
      </Typography>
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mb: 3 }}>
        {children}
      </Box>
    </>
  );
}