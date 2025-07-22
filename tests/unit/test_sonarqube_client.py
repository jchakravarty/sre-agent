import unittest
from unittest.mock import patch, MagicMock
import requests
from src.connectors.sonarqube_client import SonarQubeClient


class TestSonarQubeClient(unittest.TestCase):

    @patch('src.connectors.sonarqube_client.secrets_manager.get_secret_value')
    @patch('src.connectors.sonarqube_client.requests.get')
    def test_quality_gate_pass(self, mock_get, mock_secrets):
        """Test successful quality gate status"""
        # Mock the secrets
        mock_secrets.side_effect = lambda k: {
            'SONAR_API_URL': 'http://mock-sonar-url',
            'SONAR_API_TOKEN': 'mock-token'
        }[k]

        # Mock the API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "projectStatus": {"status": "OK"}
        }
        mock_get.return_value = mock_response

        result = SonarQubeClient().get_quality_gate_status('mock-project')
        
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertEqual(result['message'], 'SonarQube Quality Gate passed.')
        mock_get.assert_called_once()

    @patch('src.connectors.sonarqube_client.secrets_manager.get_secret_value')
    @patch('src.connectors.sonarqube_client.requests.get')
    def test_quality_gate_fail_with_conditions(self, mock_get, mock_secrets):
        """Test failed quality gate with error conditions"""
        # Mock the secrets
        mock_secrets.side_effect = lambda k: {
            'SONAR_API_URL': 'http://mock-sonar-url',
            'SONAR_API_TOKEN': 'mock-token'
        }[k]

        # Mock the API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "projectStatus": {
                "status": "ERROR",
                "conditions": [{
                    "status": "ERROR",
                    "metricKey": "coverage",
                    "actualValue": "80",
                    "errorThreshold": "90"
                }, {
                    "status": "ERROR",
                    "metricKey": "bugs",
                    "actualValue": "5",
                    "errorThreshold": "0"
                }]
            }
        }
        mock_get.return_value = mock_response

        result = SonarQubeClient().get_quality_gate_status('mock-project')
        
        self.assertEqual(result['status'], 'FAILURE')
        self.assertIn("coverage", result['message'])
        self.assertIn("bugs", result['message'])
        self.assertIn("80", result['message'])
        self.assertIn("90", result['message'])

    @patch('src.connectors.sonarqube_client.secrets_manager.get_secret_value')
    @patch('src.connectors.sonarqube_client.requests.get')
    def test_quality_gate_unknown_status(self, mock_get, mock_secrets):
        """Test quality gate with unknown status"""
        # Mock the secrets
        mock_secrets.side_effect = lambda k: {
            'SONAR_API_URL': 'http://mock-sonar-url',
            'SONAR_API_TOKEN': 'mock-token'
        }[k]

        # Mock the API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "projectStatus": {"status": "UNKNOWN"}
        }
        mock_get.return_value = mock_response

        result = SonarQubeClient().get_quality_gate_status('mock-project')
        
        self.assertEqual(result['status'], 'FAILURE')
        self.assertIn("UNKNOWN", result['message'])

    @patch('src.connectors.sonarqube_client.secrets_manager.get_secret_value')
    @patch('src.connectors.sonarqube_client.requests.get')
    def test_api_request_exception(self, mock_get, mock_secrets):
        """Test API request exception handling"""
        # Mock the secrets
        mock_secrets.side_effect = lambda k: {
            'SONAR_API_URL': 'http://mock-sonar-url',
            'SONAR_API_TOKEN': 'mock-token'
        }[k]

        # Mock an API exception
        mock_get.side_effect = requests.exceptions.RequestException('Connection error')

        with self.assertRaises(requests.exceptions.RequestException):
            SonarQubeClient().get_quality_gate_status('mock-project')

    @patch('src.connectors.sonarqube_client.secrets_manager.get_secret_value')
    @patch('src.connectors.sonarqube_client.requests.get')
    def test_api_http_error(self, mock_get, mock_secrets):
        """Test API HTTP error handling"""
        # Mock the secrets
        mock_secrets.side_effect = lambda k: {
            'SONAR_API_URL': 'http://mock-sonar-url',
            'SONAR_API_TOKEN': 'mock-token'
        }[k]

        # Mock HTTP error
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError('404 Not Found')
        mock_get.return_value = mock_response

        with self.assertRaises(requests.exceptions.HTTPError):
            SonarQubeClient().get_quality_gate_status('mock-project')


if __name__ == '__main__':
    unittest.main()
