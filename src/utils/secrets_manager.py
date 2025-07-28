"""This module contains functions for interacting with AWS Secrets Manager."""
import os
import json
import boto3

CACHED_SECRETS = None

def get_secret(secret_name):
    """
    Fetches a secret from AWS Secrets Manager and caches it globally.
    Assumes the secret value is a JSON string.
    """
    # Using a global statement here is intentional for caching secrets across
    # multiple calls within the same Lambda invocation. This avoids redundant
    # calls to AWS Secrets Manager, which can be slow and incur costs.
    global CACHED_SECRETS
    if CACHED_SECRETS:
        return CACHED_SECRETS

    print(f"Fetching secret '{secret_name}' from AWS Secrets Manager...")
    client = boto3.client('secretsmanager')

    try:
        response = client.get_secret_value(SecretId=secret_name)
        secret_string = response['SecretString']
        CACHED_SECRETS = json.loads(secret_string)
        print("Successfully fetched and cached secrets.")
        return CACHED_SECRETS
    # Catching a broad exception is intentional here. If the secrets manager
    # call fails for any reason (e.g., permissions, network), we want to
    # fall back to an empty dictionary. This allows individual clients to
    # handle missing keys gracefully (e.g., by using environment variables
    # or default values) without crashing the entire application.
    except Exception as e:
        print(f"FATAL: Could not retrieve secrets from AWS Secrets Manager: {e}")
        # In a real scenario, you might want to fail fast if secrets are essential.
        # For this agent, we'll allow individual clients to handle missing keys.
        CACHED_SECRETS = {}
        return CACHED_SECRETS

def get_secret_value(key, default=None):
    """
    Retrieves a specific value from the cached secret dictionary.
    """
    secret_name = os.environ.get("SECRETS_MANAGER_NAME")
    if not secret_name:
        # This allows for local development without needing a real secret.
        # The individual clients will use their fallback logic.
        return default

    secrets = get_secret(secret_name)
    return secrets.get(key, default)

class SecretsManager:
    @staticmethod
    def get_secret(secret_name):
        return get_secret(secret_name)

    @staticmethod
    def get_secret_value(key, default=None):
        return get_secret_value(key, default)
