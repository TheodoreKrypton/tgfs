import { Box } from "@mui/material";
import { ReactNode } from "react";

interface FieldRowProps {
  children: ReactNode;
  gap?: number;
  justifyContent?: string;
}

export function FieldRow({ children, gap = 1, justifyContent }: FieldRowProps) {
  return (
    <Box
      sx={{
        display: "flex",
        flexWrap: "wrap",
        gap,
        justifyContent,
      }}
    >
      {children}
    </Box>
  );
}
