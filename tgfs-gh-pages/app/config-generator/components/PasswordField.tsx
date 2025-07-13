import { useState } from 'react';
import { IconButton, InputAdornment } from '@mui/material';
import { Visibility, VisibilityOff } from '@mui/icons-material';
import { ConfigTextField } from './ConfigTextField';

interface PasswordFieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  helperText?: string;
  required?: boolean;
  width?: string | number;
}

export function PasswordField({ 
  label, 
  value, 
  onChange, 
  helperText, 
  required = false,
  width = 300 
}: PasswordFieldProps) {
  const [showPassword, setShowPassword] = useState(false);

  return (
    <ConfigTextField
      width={width}
      label={label}
      type={showPassword ? 'text' : 'password'}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      helperText={helperText}
      required={required}
      InputProps={{
        endAdornment: (
          <InputAdornment position="end">
            <IconButton 
              size="small" 
              onClick={() => setShowPassword(!showPassword)}
              edge="end"
            >
              {showPassword ? <VisibilityOff /> : <Visibility />}
            </IconButton>
          </InputAdornment>
        ),
      }}
    />
  );
}