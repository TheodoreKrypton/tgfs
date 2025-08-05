"use client";

import { Turnstile } from "@marsidev/react-turnstile";
import { Button } from "@mui/material";
import React from "react";

export default function JoinGroup() {
  const [success, setSuccess] = React.useState(false);
  const name1 = "tgfs**";
  const name2 = "*discussion";

  return (
    <div style={{ textAlign: "center", marginTop: "20px" }}>
      <h1>Join Telegram Group</h1>
      <div style={{ marginBottom: "20px" }} />
      {success && (
        <Button
          variant="contained"
          href={`https://t.me/${(name1 + name2).replaceAll("*", "")}`}
          target="_blank"
          rel="noopener noreferrer"
        >
          Join Support Group
        </Button>
      )}
      <div style={{ marginBottom: "20px" }} />
      <Turnstile
        siteKey="0x4AAAAAABodeku20TbzpFdm"
        onSuccess={() => setSuccess(true)}
      />
    </div>
  );
}
