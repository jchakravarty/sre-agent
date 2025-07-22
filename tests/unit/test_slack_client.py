import unittest
from unittest.mock import patch, MagicMock
import requests
from src.connectors.slack_client import SlackClient


class TestSlackClient(unittest.TestCase):

    @patch('src.connectors.slack_client.secrets_manager.get_secret_value')
    @patch('src.connectors.slack_client.requests.post')
    def test_send_notification_success(self, mock_post, mock_secret):
        """Test successful notification sending"""
        # Mock secret manager
        mock_secret.return_value = 'https://hooks.slack.com/services/test/webhook/url'
        
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        payload = {"text": "Test notification"}
        
        # Should not raise any exception
        SlackClient().send_notification(payload)
        
        mock_post.assert_called_once_with(
            'https://hooks.slack.com/services/test/webhook/url',
            json=payload,
            timeout=10
        )
        mock_response.raise_for_status.assert_called_once()

    @patch('src.connectors.slack_client.secrets_manager.get_secret_value')
    def test_send_notification_no_webhook_url(self, mock_secret):
        """Test notification when webhook URL is not configured"""
        # Mock missing secret
        mock_secret.return_value = None
        
        # Should raise ValueError when trying to initialize SlackClient
        with self.assertRaises(ValueError) as context:
            SlackClient()
        
        self.assertEqual(str(context.exception), "SLACK_WEBHOOK_URL not configured.")

    @patch('src.connectors.slack_client.secrets_manager.get_secret_value')
    @patch('src.connectors.slack_client.requests.post')
    @patch('builtins.print')
    def test_send_notification_request_exception(self, mock_print, mock_post, mock_secret):
        """Test notification with request exception"""
        # Mock secret manager
        mock_secret.return_value = 'https://hooks.slack.com/services/test/webhook/url'
        
        # Mock request exception
        mock_post.side_effect = requests.exceptions.RequestException('Connection error')
        
        payload = {"text": "Test notification"}
        
        SlackClient().send_notification(payload)
        
        # Should print error message
        mock_print.assert_called_with("Error sending notification to Slack: Connection error")

    @patch('src.connectors.slack_client.secrets_manager.get_secret_value')
    @patch('src.connectors.slack_client.requests.post')
    @patch('builtins.print')
    def test_send_notification_http_error(self, mock_print, mock_post, mock_secret):
        """Test notification with HTTP error"""
        # Mock secret manager
        mock_secret.return_value = 'https://hooks.slack.com/services/test/webhook/url'
        
        # Mock HTTP error
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError('404 Not Found')
        mock_post.return_value = mock_response
        
        payload = {"text": "Test notification"}
        
        SlackClient().send_notification(payload)
        
        # Should print error message
        mock_print.assert_called_with("Error sending notification to Slack: 404 Not Found")

    @patch('src.connectors.slack_client.secrets_manager.get_secret_value')
    def test_send_notification_empty_webhook_url(self, mock_secret):
        """Test notification with empty webhook URL"""
        # Mock empty secret
        mock_secret.return_value = ""
        
        # Should raise ValueError when trying to initialize SlackClient
        with self.assertRaises(ValueError) as context:
            SlackClient()
        
        self.assertEqual(str(context.exception), "SLACK_WEBHOOK_URL not configured.")


if __name__ == '__main__':
    unittest.main()
