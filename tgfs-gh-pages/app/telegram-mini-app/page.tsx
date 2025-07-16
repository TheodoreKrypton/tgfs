'use client';

import { useState, useEffect } from 'react';
import { Container, Paper, TextField, Button, Typography, Box, Switch, FormControlLabel, Alert, CircularProgress, ThemeProvider, CssBaseline } from '@mui/material';
import { FolderOpen, Login, Wifi, WifiOff } from '@mui/icons-material';
import Cookies from 'js-cookie';
import WebDAVClient from './webdav-client';
import FileExplorer from './file-explorer';
import { telegramTheme } from './telegram-theme';

interface LoginFormData {
  serverAddress: string;
  port: string;
  username: string;
  password: string;
  anonymous: boolean;
}

export default function TelegramMiniApp() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [webdavClient, setWebdavClient] = useState<WebDAVClient | null>(null);
  const [formData, setFormData] = useState<LoginFormData>({
    serverAddress: '',
    port: '8080',
    username: '',
    password: '',
    anonymous: false
  });

  const handle401Error = () => {
    // Clear tokens and redirect to login
    Cookies.remove('jwt_token');
    Cookies.remove('server_address');
    Cookies.remove('server_port');
    
    setIsLoggedIn(false);
    setWebdavClient(null);
    setError('Session expired. Please login again.');
  };

  // Check for existing JWT token on component mount
  useEffect(() => {
    const token = Cookies.get('jwt_token');
    const savedServerAddress = Cookies.get('server_address');
    const savedPort = Cookies.get('server_port');
    
    if (token && savedServerAddress && savedPort) {
      const baseUrl = `http://${savedServerAddress}:${savedPort}`;
      const client = new WebDAVClient(baseUrl, token, handle401Error);
      setWebdavClient(client);
      setIsLoggedIn(true);
      setFormData(prev => ({ ...prev, serverAddress: savedServerAddress, port: savedPort }));
    }
  }, []);

  const handleInputChange = (field: keyof LoginFormData) => (event: React.ChangeEvent<HTMLInputElement>) => {
    const value = event.target.type === 'checkbox' ? event.target.checked : event.target.value;
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleLogin = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const baseUrl = `http://${formData.serverAddress}:${formData.port}`;
      
      // Send login request to get JWT token
      const response = await fetch(`${baseUrl}/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username: formData.anonymous ? '' : formData.username,
          password: formData.anonymous ? '' : formData.password,
        }),
      });

      if (!response.ok) {
        throw new Error('Login failed');
      }

      const data = await response.json();
      const token = data.token;

      // Store JWT token and server info in cookies
      Cookies.set('jwt_token', token, { expires: 7 }); // 7 days expiry
      Cookies.set('server_address', formData.serverAddress, { expires: 7 });
      Cookies.set('server_port', formData.port, { expires: 7 });

      // Create WebDAV client with JWT token
      const client = new WebDAVClient(baseUrl, token, handle401Error);
      await client.connect();
      setWebdavClient(client);
      setIsLoggedIn(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setIsLoading(false);
    }
  };

  const handleLogout = () => {
    // Clear JWT token and server info from cookies
    Cookies.remove('jwt_token');
    Cookies.remove('server_address');
    Cookies.remove('server_port');
    
    setIsLoggedIn(false);
    setWebdavClient(null);
    setError(null);
  };

  return (
    <ThemeProvider theme={telegramTheme}>
      <CssBaseline />
      {isLoggedIn && webdavClient ? (
        <Container maxWidth="sm" sx={{ py: 2, minHeight: '100vh' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
            <Typography variant="h5" component="h1" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <FolderOpen />
              TGFS Explorer
            </Typography>
            <Button
              variant="outlined"
              color="secondary"
              onClick={handleLogout}
              size="small"
            >
              Logout
            </Button>
          </Box>
          <FileExplorer webdavClient={webdavClient} onAuthError={handle401Error} />
        </Container>
      ) : (
        <Container maxWidth="sm" sx={{ py: 4, minHeight: '100vh', display: 'flex', alignItems: 'center' }}>
          <Paper elevation={3} sx={{ p: 4, width: '100%' }}>
            <Typography variant="h4" component="h1" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Login />
              TGFS WebDAV Connection
            </Typography>
            
            <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
              Connect to your TGFS WebDAV server to browse and manage files stored on Telegram.
            </Typography>

            {error && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {error}
              </Alert>
            )}

            <Box component="form" sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <TextField
                label="Server Address"
                value={formData.serverAddress}
                onChange={handleInputChange('serverAddress')}
                placeholder="localhost or your-server.com"
                fullWidth
                required
                disabled={isLoading}
              />

              <TextField
                label="Port"
                value={formData.port}
                onChange={handleInputChange('port')}
                type="number"
                placeholder="8080"
                fullWidth
                required
                disabled={isLoading}
              />

              <FormControlLabel
                control={
                  <Switch
                    checked={formData.anonymous}
                    onChange={handleInputChange('anonymous')}
                    disabled={isLoading}
                  />
                }
                label={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    {formData.anonymous ? <WifiOff /> : <Wifi />}
                    Anonymous Login
                  </Box>
                }
              />

              {!formData.anonymous && (
                <>
                  <TextField
                    label="Username"
                    value={formData.username}
                    onChange={handleInputChange('username')}
                    fullWidth
                    required
                    disabled={isLoading}
                  />

                  <TextField
                    label="Password"
                    type="password"
                    value={formData.password}
                    onChange={handleInputChange('password')}
                    fullWidth
                    required
                    disabled={isLoading}
                  />
                </>
              )}

              <Button
                variant="contained"
                onClick={handleLogin}
                disabled={isLoading || !formData.serverAddress || !formData.port}
                sx={{ mt: 2 }}
                startIcon={isLoading ? <CircularProgress size={20} /> : <Login />}
              >
                {isLoading ? 'Connecting...' : 'Connect'}
              </Button>
            </Box>
          </Paper>
        </Container>
      )}
    </ThemeProvider>
  );
}