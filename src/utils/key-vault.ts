import { DefaultAzureCredential } from '@azure/identity';
import { SecretClient } from '@azure/keyvault-secrets';
import { Logger } from './logger';

/**
 * Azure Key Vault client for retrieving secrets
 */
export class KeyVaultClient {
  private client: SecretClient | null = null;
  private static instance: KeyVaultClient | null = null;

  private constructor(private vaultUrl: string) {
    if (vaultUrl) {
      try {
        const credential = new DefaultAzureCredential();
        this.client = new SecretClient(vaultUrl, credential);
        Logger.info(`Azure Key Vault client initialized for ${vaultUrl}`);
      } catch (error) {
        Logger.error(`Failed to initialize Azure Key Vault client: ${error.message}`);
        this.client = null;
      }
    }
  }

  /**
   * Get the KeyVaultClient instance
   * @param vaultUrl The URL of the Azure Key Vault
   * @returns KeyVaultClient instance
   */
  public static getInstance(vaultUrl: string): KeyVaultClient {
    if (!KeyVaultClient.instance) {
      KeyVaultClient.instance = new KeyVaultClient(vaultUrl);
    }
    return KeyVaultClient.instance;
  }

  /**
   * Get a secret from Azure Key Vault
   * @param secretName The name of the secret to retrieve
   * @returns The secret value or null if not found or error
   */
  public async getSecret(secretName: string): Promise<string | null> {
    if (!this.client) {
      Logger.warn(`Azure Key Vault client not initialized, cannot retrieve secret: ${secretName}`);
      return null;
    }

    try {
      const secret = await this.client.getSecret(secretName);
      return secret.value || null;
    } catch (error) {
      Logger.error(`Failed to retrieve secret ${secretName}: ${error.message}`);
      return null;
    }
  }

  /**
   * Check if the Key Vault client is initialized
   * @returns true if initialized, false otherwise
   */
  public isInitialized(): boolean {
    return this.client !== null;
  }
}

/**
 * Get a secret from Azure Key Vault or return a default value
 * @param client The KeyVaultClient instance
 * @param secretName The name of the secret to retrieve
 * @param defaultValue The default value to return if the secret is not found
 * @returns The secret value or the default value
 */
export async function getSecretOrDefault<T>(
  client: KeyVaultClient | null,
  secretName: string,
  defaultValue: T
): Promise<string | T> {
  if (!client || !client.isInitialized()) {
    return defaultValue;
  }

  const secretValue = await client.getSecret(secretName);
  return secretValue !== null ? secretValue : defaultValue;
} 