import unittest
from unittest.mock import patch, MagicMock
import base64
import requests
from src.connectors.git_client import GitClient


class TestGitClient(unittest.TestCase):

    @patch('src.connectors.git_client.secrets_manager.get_secret_value')
    @patch('src.connectors.git_client.requests.get')
    def test_get_file_content_success_base64(self, mock_get, mock_secrets):
        """Test successful file content retrieval with base64 encoding"""
        # Mock secrets
        mock_secrets.return_value = 'test-token'
        
        # Mock successful response with base64 content
        mock_response = MagicMock()
        mock_response.status_code = 200
        test_content = "Hello, World!"
        encoded_content = base64.b64encode(test_content.encode('utf-8')).decode('utf-8')
        mock_response.json.return_value = {
            'content': encoded_content,
            'encoding': 'base64'
        }
        mock_get.return_value = mock_response
        
        result = GitClient().get_file_content('owner/repo', 'test.txt', 'abc123')
        
        self.assertEqual(result, test_content)
        mock_get.assert_called_once_with(
            'https://api.github.com/repos/owner/repo/contents/test.txt?ref=abc123',
            headers={
                'Authorization': 'token test-token',
                'Accept': 'application/vnd.github.v3+json'
            },
            timeout=10
        )

    @patch('src.connectors.git_client.secrets_manager.get_secret_value')
    @patch('src.connectors.git_client.requests.get')
    def test_get_file_content_success_plain_text(self, mock_get, mock_secrets):
        """Test successful file content retrieval with plain text"""
        # Mock secrets
        mock_secrets.return_value = 'test-token'
        
        # Mock successful response with plain text content
        mock_response = MagicMock()
        mock_response.status_code = 200
        test_content = "Plain text content"
        mock_response.json.return_value = {
            'content': test_content,
            'encoding': 'text'
        }
        mock_get.return_value = mock_response
        
        result = GitClient().get_file_content('owner/repo', 'test.txt', 'abc123')
        
        self.assertEqual(result, test_content)

    @patch('src.connectors.git_client.secrets_manager.get_secret_value')
    @patch('src.connectors.git_client.requests.get')
    def test_get_file_content_repo_name_with_dot(self, mock_get, mock_secrets):
        """Test file content retrieval with repo name containing dot"""
        # Mock secrets
        mock_secrets.return_value = 'test-token'
        
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'content': 'test content',
            'encoding': 'text'
        }
        mock_get.return_value = mock_response
        
        result = GitClient().get_file_content('org.project', 'test.txt', 'abc123')
        
        # Check that the repo name was converted from 'org.project' to 'org/project'
        mock_get.assert_called_once_with(
            'https://api.github.com/repos/org/project/contents/test.txt?ref=abc123',
            headers={
                'Authorization': 'token test-token',
                'Accept': 'application/vnd.github.v3+json'
            },
            timeout=10
        )

    @patch('src.connectors.git_client.secrets_manager.get_secret_value')
    def test_get_file_content_no_token(self, mock_secrets):
        """Test file content retrieval without API token"""
        # Mock missing token
        mock_secrets.return_value = None
        
        with self.assertRaises(ValueError) as context:
            GitClient()
        
        self.assertEqual(str(context.exception), "GIT_API_TOKEN environment variable not set.")

    @patch('src.connectors.git_client.secrets_manager.get_secret_value')
    @patch('src.connectors.git_client.requests.get')
    @patch('builtins.print')
    def test_get_file_content_404_error(self, mock_print, mock_get, mock_secrets):
        """Test file content retrieval with 404 error"""
        # Mock secrets
        mock_secrets.return_value = 'test-token'
        
        # Mock 404 response
        mock_response = MagicMock()
        mock_response.status_code = 404
        http_error = requests.exceptions.HTTPError()
        http_error.response = mock_response
        mock_response.raise_for_status.side_effect = http_error
        mock_get.return_value = mock_response
        
        result = GitClient().get_file_content('owner/repo', 'missing.txt', 'abc123')
        
        self.assertIsNone(result)
        mock_print.assert_called_with("File 'missing.txt' not found in repo 'owner/repo' at commit 'abc123'.")

    @patch('src.connectors.git_client.secrets_manager.get_secret_value')
    @patch('src.connectors.git_client.requests.get')
    @patch('builtins.print')
    def test_get_file_content_other_http_error(self, mock_print, mock_get, mock_secrets):
        """Test file content retrieval with non-404 HTTP error"""
        # Mock secrets
        mock_secrets.return_value = 'test-token'
        
        # Mock 500 response
        mock_response = MagicMock()
        mock_response.status_code = 500
        http_error = requests.exceptions.HTTPError('Server Error')
        http_error.response = mock_response
        mock_response.raise_for_status.side_effect = http_error
        mock_get.return_value = mock_response
        
        with self.assertRaises(requests.exceptions.HTTPError):
            GitClient().get_file_content('owner/repo', 'test.txt', 'abc123')
        
        mock_print.assert_called_with("HTTP error fetching file: Server Error")

    @patch('src.connectors.git_client.secrets_manager.get_secret_value')
    @patch('src.connectors.git_client.requests.get')
    @patch('builtins.print')
    def test_get_file_content_request_exception(self, mock_print, mock_get, mock_secrets):
        """Test file content retrieval with request exception"""
        # Mock secrets
        mock_secrets.return_value = 'test-token'
        
        # Mock request exception
        mock_get.side_effect = requests.exceptions.RequestException('Connection error')
        
        with self.assertRaises(requests.exceptions.RequestException):
            GitClient().get_file_content('owner/repo', 'test.txt', 'abc123')
        
        mock_print.assert_called_with("Error fetching file from Git: Connection error")

    @patch('src.connectors.git_client.secrets_manager.get_secret_value')
    @patch('src.connectors.git_client.requests.get')
    def test_get_file_content_multiple_dots_in_repo_name(self, mock_get, mock_secrets):
        """Test file content retrieval with multiple dots in repo name"""
        # Mock secrets
        mock_secrets.return_value = 'test-token'
        
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'content': 'test content',
            'encoding': 'text'
        }
        mock_get.return_value = mock_response
        
        result = GitClient().get_file_content('org.sub.project', 'test.txt', 'abc123')
        
        # Check that only the first dot is replaced
        mock_get.assert_called_once_with(
            'https://api.github.com/repos/org/sub.project/contents/test.txt?ref=abc123',
            headers={
                'Authorization': 'token test-token',
                'Accept': 'application/vnd.github.v3+json'
            },
            timeout=10
        )


if __name__ == '__main__':
    unittest.main()
