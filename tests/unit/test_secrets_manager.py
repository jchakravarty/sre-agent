import unittest
from unittest.mock import patch, MagicMock
import json
import boto3
from src.utils.secrets_manager import get_secret, get_secret_value, CACHED_SECRETS


class TestSecretsManager(unittest.TestCase):

    def setUp(self):
        """Clear cached secrets before each test"""
        import src.utils.secrets_manager
        src.utils.secrets_manager.CACHED_SECRETS = None

    @patch('src.utils.secrets_manager.boto3.client')
    @patch('builtins.print')
    def test_get_secret_success(self, mock_print, mock_boto_client):
        """Test successful secret retrieval"""
        # Mock AWS client
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        # Mock response
        secret_data = {"key1": "value1", "key2": "value2"}
        mock_client.get_secret_value.return_value = {
            'SecretString': json.dumps(secret_data)
        }
        
        result = get_secret("test-secret")
        
        self.assertEqual(result, secret_data)
        mock_boto_client.assert_called_once_with('secretsmanager')
        mock_client.get_secret_value.assert_called_once_with(SecretId="test-secret")
        mock_print.assert_any_call("Fetching secret 'test-secret' from AWS Secrets Manager...")
        mock_print.assert_any_call("Successfully fetched and cached secrets.")

    @patch('src.utils.secrets_manager.boto3.client')
    @patch('builtins.print')
    def test_get_secret_cached(self, mock_print, mock_boto_client):
        """Test that cached secrets are returned without API call"""
        # Set up cached secrets
        import src.utils.secrets_manager
        cached_data = {"cached_key": "cached_value"}
        src.utils.secrets_manager.CACHED_SECRETS = cached_data
        
        result = get_secret("test-secret")
        
        self.assertEqual(result, cached_data)
        mock_boto_client.assert_not_called()

    @patch('src.utils.secrets_manager.boto3.client')
    @patch('builtins.print')
    def test_get_secret_exception(self, mock_print, mock_boto_client):
        """Test secret retrieval with exception"""
        # Mock AWS client
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        # Mock exception
        mock_client.get_secret_value.side_effect = Exception("AWS error")
        
        result = get_secret("test-secret")
        
        self.assertEqual(result, {})
        mock_print.assert_any_call("Fetching secret 'test-secret' from AWS Secrets Manager...")
        mock_print.assert_any_call("FATAL: Could not retrieve secrets from AWS Secrets Manager: AWS error")

    @patch('src.utils.secrets_manager.os.environ.get')
    @patch('src.utils.secrets_manager.get_secret')
    def test_get_secret_value_success(self, mock_get_secret, mock_env):
        """Test successful secret value retrieval"""
        # Mock environment variable
        mock_env.return_value = "test-secret-name"
        
        # Mock secret data
        secret_data = {"api_key": "secret123", "db_password": "dbpass456"}
        mock_get_secret.return_value = secret_data
        
        result = get_secret_value("api_key")
        
        self.assertEqual(result, "secret123")
        mock_get_secret.assert_called_once_with("test-secret-name")

    @patch('src.utils.secrets_manager.os.environ.get')
    @patch('src.utils.secrets_manager.get_secret')
    def test_get_secret_value_with_default(self, mock_get_secret, mock_env):
        """Test secret value retrieval with default value"""
        # Mock environment variable
        mock_env.return_value = "test-secret-name"
        
        # Mock secret data without the requested key
        secret_data = {"other_key": "other_value"}
        mock_get_secret.return_value = secret_data
        
        result = get_secret_value("missing_key", "default_value")
        
        self.assertEqual(result, "default_value")

    @patch('src.utils.secrets_manager.os.environ.get')
    def test_get_secret_value_no_secret_name(self, mock_env):
        """Test secret value retrieval when secret name is not configured"""
        # Mock missing environment variable
        mock_env.return_value = None
        
        result = get_secret_value("api_key", "default_value")
        
        self.assertEqual(result, "default_value")

    @patch('src.utils.secrets_manager.os.environ.get')
    def test_get_secret_value_no_secret_name_no_default(self, mock_env):
        """Test secret value retrieval when secret name is not configured and no default"""
        # Mock missing environment variable
        mock_env.return_value = None
        
        result = get_secret_value("api_key")
        
        self.assertIsNone(result)

    @patch('src.utils.secrets_manager.boto3.client')
    @patch('builtins.print')
    def test_get_secret_invalid_json(self, mock_print, mock_boto_client):
        """Test secret retrieval with invalid JSON"""
        # Mock AWS client
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        # Mock response with invalid JSON
        mock_client.get_secret_value.return_value = {
            'SecretString': 'invalid json string'
        }
        
        result = get_secret("test-secret")
        
        self.assertEqual(result, {})
        mock_print.assert_any_call("Fetching secret 'test-secret' from AWS Secrets Manager...")


if __name__ == '__main__':
    unittest.main()
