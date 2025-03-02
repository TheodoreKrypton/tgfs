#!/bin/bash

# Log Azure identity information if debugging is enabled
if [ "$AZURE_DEBUG" = "true" ]; then
  echo "Checking Azure identity..."
  az login --identity || echo "Failed to login with managed identity, but continuing..."
  az keyvault list || echo "Failed to list key vaults, but continuing..."
fi

# Run the application
node /tgfs/index.js $@