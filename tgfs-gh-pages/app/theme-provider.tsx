'use client';

import { createTheme, ThemeProvider as MuiThemeProvider, CssBaseline } from '@mui/material';
import { ReactNode } from 'react';

const darkTheme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#90caf9',
    },
    secondary: {
      main: '#f48fb1',
    },
    background: {
      default: '#121212',
      paper: '#1e1e1e',
    },
  },
  typography: {
    fontFamily: 'var(--font-geist-sans)',
    h1: {
      fontFamily: 'var(--font-geist-sans)',
    },
    h2: {
      fontFamily: 'var(--font-geist-sans)',
    },
    h3: {
      fontFamily: 'var(--font-geist-sans)',
    },
    h4: {
      fontFamily: 'var(--font-geist-sans)',
    },
    h5: {
      fontFamily: 'var(--font-geist-sans)',
    },
    h6: {
      fontFamily: 'var(--font-geist-sans)',
    },
  },
});

interface ThemeProviderProps {
  children: ReactNode;
}

export function ThemeProvider({ children }: ThemeProviderProps) {
  return (
    <MuiThemeProvider theme={darkTheme}>
      <CssBaseline />
      {children}
    </MuiThemeProvider>
  );
}