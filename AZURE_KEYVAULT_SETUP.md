# Azure Key Vault Integration for TGFS

This document provides instructions for setting up TGFS with Azure Key Vault integration to securely store sensitive configuration values.

## Prerequisites

- An Azure subscription
- An Azure Key Vault
- An Azure VM with a managed identity (for production use)

## Setting Up Azure Key Vault

1. Create an Azure Key Vault in your Azure subscription:

```bash
az keyvault create --name your-keyvault-name --resource-group your-resource-group --location your-location
```

2. Add the required secrets to your Key Vault:

```bash
# Telegram API ID
az keyvault secret set --vault-name your-keyvault-name --name tgfs-api-id --value "your-api-id"

# Telegram API Hash
az keyvault secret set --vault-name your-keyvault-name --name tgfs-api-hash --value "your-api-hash"

# Telegram Bot Token
az keyvault secret set --vault-name your-keyvault-name --name tgfs-bot-token --value "your-bot-token"

# Private File Channel ID
az keyvault secret set --vault-name your-keyvault-name --name tgfs-private-file-channel --value "your-channel-id"

# JWT Secret
az keyvault secret set --vault-name your-keyvault-name --name tgfs-jwt-secret --value "your-jwt-secret"

# User Passwords (one for each user)
az keyvault secret set --vault-name your-keyvault-name --name tgfs-user-password-admin --value "admin-password"
az keyvault secret set --vault-name your-keyvault-name --name tgfs-user-password-user --value "user-password"
```

## Setting Up Azure VM with Managed Identity

1. Create an Azure VM with a system-assigned managed identity:

```bash
az vm create \
  --resource-group your-resource-group \
  --name your-vm-name \
  --image UbuntuLTS \
  --admin-username azureuser \
  --generate-ssh-keys \
  --assign-identity
```

Or enable managed identity on an existing VM:

```bash
az vm identity assign --resource-group your-resource-group --name your-vm-name
```

2. Grant the VM's managed identity access to your Key Vault:

```bash
# Get the VM's managed identity principal ID
PRINCIPAL_ID=$(az vm identity show --resource-group your-resource-group --name your-vm-name --query principalId -o tsv)

# Grant the managed identity "Get" permissions for secrets in the Key Vault
az keyvault set-policy --name your-keyvault-name --object-id $PRINCIPAL_ID --secret-permissions get
```

## Configuring TGFS

1. Create a configuration file (e.g., `config-azure.yaml`) with Azure Key Vault settings:

```yaml
azure:
  key_vault:
    url: https://your-keyvault-name.vault.azure.net/
    enabled: true
    secret_mapping:
      api_id: tgfs-api-id
      api_hash: tgfs-api-hash
      bot_token: tgfs-bot-token
      private_file_channel: tgfs-private-file-channel
      password: tgfs-user-password
      jwt_secret: tgfs-jwt-secret

# Rest of your configuration...
```

2. Run TGFS with the configuration file:

```bash
tgfs -f config-azure.yaml
```

## Running in Docker

1. Build the Docker image:

```bash
docker build -t tgfs .
```

2. Run the Docker container with the configuration file:

```bash
docker run -v /path/to/config-azure.yaml:/config.yaml -p 1900:1900 -p 1901:1901 tgfs -f /config.yaml
```

## Troubleshooting

If you encounter issues with Azure Key Vault integration:

1. Enable Azure debugging:

```bash
export AZURE_DEBUG=true
```

2. Check if the managed identity is working:

```bash
az login --identity
```

3. Verify that the managed identity has access to the Key Vault:

```bash
az keyvault secret list --vault-name your-keyvault-name
```

4. Check the logs for any Azure Key Vault related errors.

## Local Development

For local development or when running outside of Azure:

1. Set `azure.key_vault.enabled` to `false` to use values directly from the config file, or
2. Use Azure CLI to authenticate (`az login`) before running TGFS, or
3. Use environment variables for Azure authentication:

```bash
export AZURE_CLIENT_ID=your-client-id
export AZURE_CLIENT_SECRET=your-client-secret
export AZURE_TENANT_ID=your-tenant-id
``` 