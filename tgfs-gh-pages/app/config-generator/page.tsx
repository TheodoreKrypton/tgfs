'use client';

import { useState } from 'react';
import {
  Box,
  Container,
  Typography,
  Paper,
  Button,
  Card,
  CardContent,
  Alert,
  AlertTitle,
} from '@mui/material';
import {
  Download,
  ContentCopy,
  Add,
} from '@mui/icons-material';
import yaml from 'js-yaml';
import { ConfigTextField } from './components/ConfigTextField';
import { PasswordField } from './components/PasswordField';
import { FormSection } from './components/FormSection';
import { BotTokenField } from './components/BotTokenField';
import { FieldRow } from './components/FieldRow';

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
      [key: string]: {
        password: string;
      };
    };
    download: {
      chunk_size_kb: number;
    };
  };
  webdav: {
    host: string;
    port: number;
    path: string;
  };
}

export default function ConfigGenerator() {
  
  const [config, setConfig] = useState<ConfigData>({
    telegram: {
      api_id: '',
      api_hash: '',
      account: {
        session_file: 'account.session',
      },
      bot: {
        session_file: 'bot.session',
        tokens: [''],
      },
      private_file_channel: '',
      public_file_channel: 0,
    },
    tgfs: {
      users: {
        user: {
          password: 'password',
        },
      },
      download: {
        chunk_size_kb: 1024,
      },
    },
    webdav: {
      host: '0.0.0.0',
      port: 1900,
      path: '/',
    },
  });

  const updateConfig = (path: string, value: any) => {
    const keys = path.split('.');
    const newConfig = { ...config };
    let current: any = newConfig;
    
    for (let i = 0; i < keys.length - 1; i++) {
      current = current[keys[i]];
    }
    current[keys[keys.length - 1]] = value;
    
    setConfig(newConfig);
  };

  const addBotToken = () => {
    const newTokens = [...config.telegram.bot.tokens, ''];
    updateConfig('telegram.bot.tokens', newTokens);
  };

  const removeBotToken = (index: number) => {
    const newTokens = config.telegram.bot.tokens.filter((_, i) => i !== index);
    updateConfig('telegram.bot.tokens', newTokens);
  };

  const updateBotToken = (index: number, value: string) => {
    const newTokens = [...config.telegram.bot.tokens];
    newTokens[index] = value;
    updateConfig('telegram.bot.tokens', newTokens);
  };

  const generateYaml = () => {
    return yaml.dump(config, { indent: 2 });
  };

  const downloadConfig = () => {
    const yamlContent = generateYaml();
    const blob = new Blob([yamlContent], { type: 'text/yaml' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'config.yaml';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const copyToClipboard = () => {
    const yamlContent = generateYaml();
    navigator.clipboard.writeText(yamlContent);
  };

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Typography variant="h3" component="h1" gutterBottom align="center">
        TGFS Config Generator
      </Typography>
      
      <Typography variant="h6" color="text.secondary" align="center" sx={{ mb: 4 }}>
        Generate your TGFS configuration file with this interactive form
      </Typography>

      <Alert severity="warning" sx={{ mb: 3 }}>
        <AlertTitle>Important</AlertTitle>
        Keep your API credentials and bot tokens secure. Never share them publicly.
      </Alert>

      <Box sx={{ display: 'flex', gap: 3, flexDirection: { xs: 'column', md: 'row' } }}>
        <Box sx={{ flex: 1 }}>
          <Paper sx={{ p: 3 }}>
            <FormSection title="Telegram Configuration" showDivider={false}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
                <Typography variant="h6">
                  API Credentials
                </Typography>
                <Button
                  variant="outlined"
                  size="small"
                  component="a"
                  href="https://my.telegram.org/apps"
                  target="_blank"
                  rel="noopener noreferrer"
                  sx={{ textTransform: 'none' }}
                >
                  Get API Keys
                </Button>
              </Box>
              <FieldRow>
                <ConfigTextField
                  label="API ID"
                  value={config.telegram.api_id}
                  onChange={(e) => updateConfig('telegram.api_id', e.target.value)}
                  required
                />
                <PasswordField
                  label="API Hash"
                  value={config.telegram.api_hash}
                  onChange={(value) => updateConfig('telegram.api_hash', value)}
                  required
                />
              </FieldRow>
              
              <ConfigTextField
                label="Private File Channel ID"
                value={config.telegram.private_file_channel}
                onChange={(e) => updateConfig('telegram.private_file_channel', e.target.value)}
                helperText="Channel ID (numeric, e.g., 1234567)"
                required
                width={400}
              />

              <Box>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mt: 2, mb: 2 }}>
                  <Typography variant="h6">
                    Bot Tokens
                  </Typography>
                  <Button
                    variant="outlined"
                    size="small"
                    component="a"
                    href="https://t.me/botfather"
                    target="_blank"
                    rel="noopener noreferrer"
                    sx={{ textTransform: 'none' }}
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
                    onDelete={index > 0 ? () => removeBotToken(index) : undefined}
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

            <FormSection title="TGFS Configuration">
              <FieldRow>
                <ConfigTextField
                  label="Username"
                  value={Object.keys(config.tgfs.users)[0]}
                  onChange={(e) => {
                    const newUsers = { [e.target.value]: config.tgfs.users.user };
                    updateConfig('tgfs.users', newUsers);
                  }}
                />
                <PasswordField
                  label="Password"
                  value={config.tgfs.users.user.password}
                  onChange={(value) => updateConfig('tgfs.users.user.password', value)}
                />
                <ConfigTextField
                  label="Download Chunk Size (KB)"
                  type="number"
                  value={config.tgfs.download.chunk_size_kb}
                  onChange={(e) => updateConfig('tgfs.download.chunk_size_kb', parseInt(e.target.value))}
                  width={200}
                />
              </FieldRow>
            </FormSection>

            <FormSection title="WebDAV Server">
              <FieldRow>
                <ConfigTextField
                  label="Host"
                  value={config.webdav.host}
                  onChange={(e) => updateConfig('webdav.host', e.target.value)}
                  width={200}
                />
                <ConfigTextField
                  label="Port"
                  type="number"
                  value={config.webdav.port}
                  onChange={(e) => updateConfig('webdav.port', parseInt(e.target.value))}
                  width={120}
                />
                <ConfigTextField
                  label="Path"
                  value={config.webdav.path}
                  onChange={(e) => updateConfig('webdav.path', e.target.value)}
                  width={120}
                />
              </FieldRow>
            </FormSection>

          </Paper>
        </Box>

        <Box sx={{ width: { xs: '100%', md: '400px' }, flexShrink: 0 }}>
          <Paper sx={{ p: 3, position: 'sticky', top: 24 }}>
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
              <CardContent>
                <Typography variant="body2" component="pre" sx={{ 
                  fontSize: '0.75rem',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                  maxHeight: '400px',
                  overflow: 'auto'
                }}>
                  {generateYaml()}
                </Typography>
              </CardContent>
            </Card>

            <Box sx={{ mt: 2 }}>
              <Typography variant="body2" color="text.secondary">
                <strong>Next steps:</strong>
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                1. Download the config file<br/>
                2. Place it in your .tgfs directory<br/>
                3. Add your bot to the channel as admin<br/>
                4. Run TGFS with Docker
              </Typography>
            </Box>
          </Paper>
        </Box>
      </Box>
    </Container>
  );
}