import unittest
from unittest.mock import patch, MagicMock
import requests
from src.connectors.wiz_client import WizClient


class TestWizClient(unittest.TestCase):

    @patch('src.connectors.wiz_client.secrets_manager.get_secret_value')
    @patch('src.connectors.wiz_client.requests.get')
    def test_get_cve_status_success_no_vulnerabilities(self, mock_get, mock_secret):
        """Test successful CVE status check with no vulnerabilities"""
        # Mock successful response with no vulnerabilities
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"count": 0}
        mock_get.return_value = mock_response
        mock_secret.side_effect = lambda k: 'test-token' if k == 'WIZ_API_TOKEN' else 'https://api.wiz.io'
        
        result = WizClient().get_cve_status('test-artifact-id')
        
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertEqual(result['message'], 'Wiz scan passed. No new critical CVEs found.')
        
        mock_get.assert_called_once_with(
            'https://api.wiz.io/api/v1/images',
            params={
                'filter[name]': 'test-artifact-id',
                'filter[vulnerabilities][severity]': 'Critical',
                'count': 1
            },
            headers={
                'Authorization': 'Bearer test-token',
                'Content-Type': 'application/json'
            },
            timeout=10
        )

    @patch('src.connectors.wiz_client.secrets_manager.get_secret_value')
    @patch('src.connectors.wiz_client.requests.get')
    def test_get_cve_status_vulnerabilities_found(self, mock_get, mock_secret):
        """Test CVE status check with vulnerabilities found"""
        # Mock successful response with vulnerabilities
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"count": 3}
        mock_get.return_value = mock_response
        mock_secret.side_effect = lambda k: 'test-token' if k == 'WIZ_API_TOKEN' else 'https://api.wiz.io'
        
        result = WizClient().get_cve_status('vulnerable-artifact')
        
        self.assertEqual(result['status'], 'FAILURE')
        self.assertEqual(result['message'], "Wiz found critical vulnerabilities for artifact 'vulnerable-artifact'.")

    @patch('src.connectors.wiz_client.secrets_manager.get_secret_value')
    def test_get_cve_status_no_token(self, mock_secret):
        """Test CVE status check without API token"""
        mock_secret.side_effect = lambda k: None if k == 'WIZ_API_TOKEN' else 'https://api.wiz.io'
        with self.assertRaises(ValueError) as context:
            WizClient()
        
        self.assertEqual(str(context.exception), "Wiz API URL or Token not configured.")

    @patch('src.connectors.wiz_client.secrets_manager.get_secret_value')
    def test_get_cve_status_no_url(self, mock_secret):
        """Test CVE status check without API URL"""
        mock_secret.side_effect = lambda k: 'test-token' if k == 'WIZ_API_TOKEN' else None
        with self.assertRaises(ValueError) as context:
            WizClient()
        
        self.assertEqual(str(context.exception), "Wiz API URL or Token not configured.")

    @patch('src.connectors.wiz_client.secrets_manager.get_secret_value')
    @patch('src.connectors.wiz_client.requests.get')
    @patch('builtins.print')
    def test_get_cve_status_request_exception(self, mock_print, mock_get, mock_secret):
        """Test CVE status check with request exception"""
        # Mock request exception
        mock_get.side_effect = requests.exceptions.RequestException('Connection error')
        mock_secret.side_effect = lambda k: 'test-token' if k == 'WIZ_API_TOKEN' else 'https://api.wiz.io'
        with self.assertRaises(requests.exceptions.RequestException):
            WizClient().get_cve_status('test-artifact-id')
        
        mock_print.assert_called_with("Error fetching Wiz status: Connection error")

    @patch('src.connectors.wiz_client.secrets_manager.get_secret_value')
    @patch('src.connectors.wiz_client.requests.get')
    @patch('builtins.print')
    def test_get_cve_status_http_error(self, mock_print, mock_get, mock_secret):
        """Test CVE status check with HTTP error"""
        # Mock HTTP error
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError('401 Unauthorized')
        mock_get.return_value = mock_response
        mock_secret.side_effect = lambda k: 'test-token' if k == 'WIZ_API_TOKEN' else 'https://api.wiz.io'
        with self.assertRaises(requests.exceptions.HTTPError):
            WizClient().get_cve_status('test-artifact-id')
        
        mock_print.assert_called_with("Error fetching Wiz status: 401 Unauthorized")

    @patch('src.connectors.wiz_client.secrets_manager.get_secret_value')
    @patch('src.connectors.wiz_client.requests.get')
    def test_get_cve_status_missing_count_field(self, mock_get, mock_secret):
        """Test CVE status check with missing count field in response"""
        # Mock response without count field
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"other_field": "value"}
        mock_get.return_value = mock_response
        mock_secret.side_effect = lambda k: 'test-token' if k == 'WIZ_API_TOKEN' else 'https://api.wiz.io'
        
        result = WizClient().get_cve_status('test-artifact-id')
        
        # Should default to 0 when count is missing
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertEqual(result['message'], 'Wiz scan passed. No new critical CVEs found.')

    @patch('src.connectors.wiz_client.secrets_manager.get_secret_value')
    def test_get_cve_status_empty_token(self, mock_secret):
        """Test CVE status check with empty API token"""
        mock_secret.side_effect = lambda k: '' if k == 'WIZ_API_TOKEN' else 'https://api.wiz.io'
        with self.assertRaises(ValueError) as context:
            WizClient()
        
        self.assertEqual(str(context.exception), "Wiz API URL or Token not configured.")

    @patch('src.connectors.wiz_client.secrets_manager.get_secret_value')
    def test_get_cve_status_empty_url(self, mock_secret):
        """Test CVE status check with empty API URL"""
        mock_secret.side_effect = lambda k: 'test-token' if k == 'WIZ_API_TOKEN' else ''
        with self.assertRaises(ValueError) as context:
            WizClient()
        
        self.assertEqual(str(context.exception), "Wiz API URL or Token not configured.")


if __name__ == '__main__':
    unittest.main()
