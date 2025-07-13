import { Box } from '@mui/material';
import { ReactNode } from 'react';

interface FieldRowProps {
  children: ReactNode;
  gap?: number;
}

export function FieldRow({ children, gap = 2 }: FieldRowProps) {
  return (
    <Box sx={{ 
      display: 'flex', 
      flexWrap: 'wrap',
      gap,
      alignItems: 'flex-start'
    }}>
      {children}
    </Box>
  );
}