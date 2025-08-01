"use client";

import Link from "next/link";
import {
  Stepper,
  Step,
  StepLabel,
  StepContent,
  Typography,
  Button,
  TextField,
  Box,
} from "@mui/material";
import { ArrowBack, Settings, Apps } from "@mui/icons-material";
import { useState } from "react";

export default function GettingStarted() {
  const [activeStep, setActiveStep] = useState(0);

  const [dockerConfig, setDockerConfig] = useState({
    tgfsPort: 1900,
    mountedVolume: "/home/username/.tgfs",
    managerPort: 1901,
  });

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
      <div className="container mx-auto px-6 py-12 max-w-4xl">
        <header className="text-center mb-12">
          <Link
            href="/"
            className="inline-flex items-center text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white mb-6 transition-colors"
          >
            <ArrowBack className="w-5 h-5 mr-2" />
            Back to Home
          </Link>
          <h1 className="text-4xl font-bold text-slate-900 dark:text-white mb-4">
            Getting Started with TGFS
          </h1>
          <p className="text-xl text-slate-600 dark:text-slate-300">
            Follow these steps to set up your Telegram File System
          </p>
        </header>

        <div className="bg-white dark:bg-slate-800 rounded-xl p-8 shadow-lg border border-slate-200 dark:border-slate-700">
          <Stepper activeStep={activeStep} orientation="vertical">
            <Step>
              <StepLabel
                onClick={() => setActiveStep(0)}
                sx={{ cursor: "pointer" }}
              >
                <Typography
                  variant="h6"
                  className="text-slate-900 dark:text-white"
                >
                  Create a Telegram App
                </Typography>
              </StepLabel>
              <StepContent>
                <Typography
                  className="text-slate-600 dark:text-slate-300"
                  sx={{ marginBottom: 3 }}
                >
                  First, you need to create a Telegram app to get your API
                  credentials.
                </Typography>
                <ol
                  className="list-decimal list-inside text-slate-600 dark:text-slate-300"
                  style={{ marginBottom: "24px" }}
                >
                  <li style={{ marginBottom: "12px" }}>
                    Go to{" "}
                    <a
                      href="https://my.telegram.org/apps"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-500 hover:text-blue-600 underline"
                    >
                      https://my.telegram.org/apps
                    </a>
                  </li>
                  <li style={{ marginBottom: "12px" }}>
                    Login with your phone number
                  </li>
                  <li style={{ marginBottom: "12px" }}>
                    Create a new Telegram app by filling in the required details
                  </li>
                </ol>
                <div style={{ marginTop: "24px" }}>
                  <Button
                    variant="contained"
                    onClick={() => setActiveStep(1)}
                    sx={{ mr: 1 }}
                  >
                    Continue
                  </Button>
                </div>
              </StepContent>
            </Step>

            <Step>
              <StepLabel
                onClick={() => setActiveStep(1)}
                sx={{ cursor: "pointer" }}
              >
                <Typography
                  variant="h6"
                  className="text-slate-900 dark:text-white"
                >
                  Create a Private Telegram Channel
                </Typography>
              </StepLabel>
              <StepContent>
                <Typography
                  className="text-slate-600 dark:text-slate-300"
                  sx={{ marginBottom: 3 }}
                >
                  Create a private Telegram channel where TGFS will store your
                  files.
                </Typography>
                <div style={{ marginTop: "24px" }}>
                  <Button
                    variant="contained"
                    onClick={() => setActiveStep(2)}
                    sx={{ mr: 1 }}
                  >
                    Continue
                  </Button>
                </div>
              </StepContent>
            </Step>

            <Step>
              <StepLabel
                onClick={() => setActiveStep(2)}
                sx={{ cursor: "pointer" }}
              >
                <Typography
                  variant="h6"
                  className="text-slate-900 dark:text-white"
                >
                  Create a Telegram Bot
                </Typography>
              </StepLabel>
              <StepContent>
                <Typography
                  className="text-slate-600 dark:text-slate-300"
                  sx={{ marginBottom: 3 }}
                >
                  Next, create a (or many) Telegram bot that handles channel
                  messages on behalf of you.
                </Typography>
                <ol
                  className="list-decimal list-inside text-slate-600 dark:text-slate-300"
                  style={{ marginBottom: "24px" }}
                >
                  <li style={{ marginBottom: "12px" }}>
                    Open&nbsp;
                    <a
                      href="https://t.me/botfather"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center px-3 py-1 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors text-sm"
                    >
                      @BotFather
                    </a>
                  </li>
                  <li style={{ marginBottom: "12px" }}>
                    Send{" "}
                    <code className="bg-slate-100 dark:bg-slate-700 px-2 py-1 rounded">
                      /newbot
                    </code>{" "}
                    to create a new bot
                  </li>
                  <li style={{ marginBottom: "12px" }}>
                    Add your bot to the private channel you created in the
                    previous step, and <b>make it an admin</b>.
                  </li>
                </ol>
                <div style={{ marginTop: "24px" }}>
                  <Button
                    variant="contained"
                    onClick={() => setActiveStep(3)}
                    sx={{ mr: 1 }}
                  >
                    Continue
                  </Button>
                </div>
              </StepContent>
            </Step>

            <Step>
              <StepLabel
                onClick={() => setActiveStep(3)}
                sx={{ cursor: "pointer" }}
              >
                <Typography
                  variant="h6"
                  className="text-slate-900 dark:text-white"
                >
                  Generate Configuration
                </Typography>
              </StepLabel>
              <StepContent>
                <Typography
                  className="text-slate-600 dark:text-slate-300"
                  sx={{ marginBottom: 3 }}
                >
                  Use our config generator to create your TGFS configuration
                  file.
                </Typography>
                <div style={{ marginBottom: "24px" }}>
                  <Link
                    href="/config-generator"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
                  >
                    <Settings className="w-5 h-5 mr-2" />
                    Open Config Generator
                  </Link>
                </div>
                <div style={{ marginTop: "24px" }}>
                  <Button
                    variant="contained"
                    onClick={() => setActiveStep(4)}
                    sx={{ mr: 1 }}
                  >
                    Continue
                  </Button>
                </div>
              </StepContent>
            </Step>

            <Step>
              <StepLabel
                onClick={() => setActiveStep(4)}
                sx={{ cursor: "pointer" }}
              >
                <Typography
                  variant="h6"
                  className="text-slate-900 dark:text-white"
                >
                  Run TGFS Server
                </Typography>
              </StepLabel>
              <StepContent>
                <Typography
                  className="text-slate-600 dark:text-slate-300"
                  sx={{ marginBottom: 3 }}
                >
                  Configure the Docker settings for running TGFS:
                </Typography>

                <Box sx={{ marginBottom: 3, display: "flex", gap: 4 }}>
                  <TextField
                    label="TGFS Port"
                    type="number"
                    value={dockerConfig.tgfsPort}
                    onChange={(e) =>
                      setDockerConfig((prev) => ({
                        ...prev,
                        tgfsPort: parseInt(e.target.value) || 1900,
                      }))
                    }
                    helperText="Port for TGFS WebDAV server"
                  />

                  <TextField
                    label="Manager Port"
                    type="number"
                    value={dockerConfig.managerPort}
                    onChange={(e) =>
                      setDockerConfig((prev) => ({
                        ...prev,
                        managerPort: parseInt(e.target.value) || 1901,
                      }))
                    }
                    helperText="Port for TGFS manager server"
                  />

                  <TextField
                    label="Mounted Volume Path"
                    value={dockerConfig.mountedVolume}
                    onChange={(e) =>
                      setDockerConfig((prev) => ({
                        ...prev,
                        mountedVolume: e.target.value,
                      }))
                    }
                    helperText="Place of config.yaml file"
                  />
                </Box>
                <div
                  className="bg-slate-100 dark:bg-slate-700 rounded-lg p-4"
                  style={{ marginBottom: "24px" }}
                >
                  <code className="text-sm text-slate-700 dark:text-slate-300 block break-all">
                    docker run -it -v {dockerConfig.mountedVolume}
                    :/home/tgfs/.tgfs -p {dockerConfig.tgfsPort}:
                    {dockerConfig.tgfsPort} -p {dockerConfig.managerPort}:
                    {dockerConfig.managerPort} wheatcarrier/tgfs
                  </code>
                </div>

                <div style={{ marginTop: "24px" }}>
                  <Button
                    variant="contained"
                    onClick={() => setActiveStep(5)}
                    sx={{ mr: 1 }}
                  >
                    Continue
                  </Button>
                </div>
              </StepContent>
            </Step>

            <Step>
              <StepLabel
                onClick={() => setActiveStep(5)}
                sx={{ cursor: "pointer" }}
              >
                <Typography
                  variant="h6"
                  className="text-slate-900 dark:text-white"
                >
                  Start Using TGFS
                </Typography>
              </StepLabel>
              <StepContent>
                <Typography
                  className="text-slate-600 dark:text-slate-300"
                  sx={{ marginBottom: 3 }}
                >
                  Once everything is set up, you can access your files through
                  these tested WebDAV clients:
                </Typography>
                <ul
                  className="list-disc list-inside text-slate-600 dark:text-slate-300"
                  style={{ marginBottom: "32px" }}
                >
                  <li style={{ marginBottom: "12px" }}>
                    <a
                      href="https://rclone.org/"
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      rclone
                    </a>
                  </li>
                  <li style={{ marginBottom: "12px" }}>
                    <a
                      href="https://cyberduck.io/"
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      CyberDuck
                    </a>
                  </li>
                  <li style={{ marginBottom: "12px" }}>
                    <a
                      href="https://winscp.net/"
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      WinSCP
                    </a>
                  </li>
                  <li style={{ marginBottom: "12px" }}>
                    <a
                      href="https://davdroid.com/"
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      DavDroid
                    </a>
                  </li>
                </ul>
                <Typography
                  className="text-slate-600 dark:text-slate-300"
                  sx={{ marginBottom: 3 }}
                >
                  You can also access your files through the official Telegram
                  Mini App:
                </Typography>
                <div style={{ marginBottom: "24px" }}>
                  <Link
                    href="https://t.me/tgfsprdbot/manager"
                    className="inline-flex items-center px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors"
                  >
                    <Apps className="w-5 h-5 mr-2" />
                    Try Mini App
                  </Link>
                </div>
              </StepContent>
            </Step>
          </Stepper>
        </div>
      </div>
    </div>
  );
}
