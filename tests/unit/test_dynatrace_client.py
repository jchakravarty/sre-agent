import unittest
from unittest.mock import patch, MagicMock
import requests
import time
from src.connectors.dynatrace_client import DynatraceClient, trace_function


class TestDynatraceClient(unittest.TestCase):

    @patch('src.connectors.dynatrace_client.secrets_manager.get_secret_value')
    @patch('src.connectors.dynatrace_client.requests.post')
    @patch('builtins.print')
    def test_send_event_success(self, mock_print, mock_post, mock_secrets):
        """Test successful event sending"""
        # Mock secrets
        mock_secrets.side_effect = lambda k: {
            'DYNATRACE_API_URL': 'https://mock-dynatrace-url',
            'DYNATRACE_API_TOKEN': 'mock-token'
        }[k]
        
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        event_payload = {
            "eventType": "CUSTOM_INFO",
            "title": "Test Event",
            "entitySelector": "type(CUSTOM_DEVICE)"
        }
        
        DynatraceClient().send_event(event_payload)
        
        mock_post.assert_called_once_with(
            'https://mock-dynatrace-url/api/v2/events/ingest',
            headers={
                "Authorization": "Api-Token mock-token",
                "Content-Type": "application/json"
            },
            json=event_payload,
            timeout=10
        )
        mock_print.assert_called_with("Successfully sent event to Dynatrace: Test Event")

    @patch('src.connectors.dynatrace_client.secrets_manager.get_secret_value')
    def test_send_event_no_credentials(self, mock_secrets):
        """Test event sending when credentials are not configured"""
        # Mock missing secrets
        mock_secrets.return_value = None
        
        # Should raise ValueError when trying to initialize DynatraceClient
        with self.assertRaises(ValueError) as context:
            DynatraceClient()
        
        self.assertEqual(str(context.exception), "Dynatrace API URL or Token not configured.")

    @patch('src.connectors.dynatrace_client.secrets_manager.get_secret_value')
    @patch('src.connectors.dynatrace_client.requests.post')
    @patch('builtins.print')
    def test_send_event_request_exception(self, mock_print, mock_post, mock_secrets):
        """Test event sending with request exception"""
        # Mock secrets
        mock_secrets.side_effect = lambda k: {
            'DYNATRACE_API_URL': 'https://mock-dynatrace-url',
            'DYNATRACE_API_TOKEN': 'mock-token'
        }[k]
        
        # Mock request exception
        mock_post.side_effect = requests.exceptions.RequestException('Connection error')
        
        event_payload = {"title": "Test Event"}
        
        DynatraceClient().send_event(event_payload)
        
        mock_print.assert_called_with("Error sending event to Dynatrace: Connection error")

    @patch('src.connectors.dynatrace_client.DynatraceClient.__init__', return_value=None)
    @patch.object(DynatraceClient, 'send_event')
    @patch('time.time')
    def test_trace_function_success(self, mock_time, mock_send_event, mock_init):
        """Test trace function decorator with successful execution"""
        # Mock time progression
        mock_time.side_effect = [1000.0, 1001.5]  # 1.5 seconds duration
        
        @trace_function
        def test_function(repo_name):
            return "success result"
        
        result = test_function("test-repo")
        
        self.assertEqual(result, "success result")
        self.assertEqual(mock_send_event.call_count, 2)
        
        # Check start event
        start_call = mock_send_event.call_args_list[0][0][0]
        self.assertEqual(start_call["eventType"], "CUSTOM_INFO")
        self.assertEqual(start_call["title"], "Function Started: test_function")
        self.assertEqual(start_call["properties"]["status"], "STARTED")
        
        # Check finish event
        finish_call = mock_send_event.call_args_list[1][0][0]
        self.assertEqual(finish_call["eventType"], "CUSTOM_INFO")
        self.assertEqual(finish_call["title"], "Function Finished: test_function")
        self.assertEqual(finish_call["properties"]["status"], "SUCCESS")
        self.assertEqual(finish_call["properties"]["duration_ms"], 1500.0)

    @patch('src.connectors.dynatrace_client.DynatraceClient.__init__', return_value=None)
    @patch.object(DynatraceClient, 'send_event')
    @patch('time.time')
    @patch('builtins.print')
    def test_trace_function_failure(self, mock_print, mock_time, mock_send_event, mock_init):
        """Test trace function decorator with function failure"""
        # Mock time progression
        mock_time.side_effect = [1000.0, 1001.0]  # 1 second duration
        
        @trace_function
        def failing_function(repo_name):
            raise ValueError("Test error")
        
        with self.assertRaises(ValueError):
            failing_function("test-repo")
        
        self.assertEqual(mock_send_event.call_count, 2)
        
        # Check start event
        start_call = mock_send_event.call_args_list[0][0][0]
        self.assertEqual(start_call["properties"]["status"], "STARTED")
        
        # Check fail event
        fail_call = mock_send_event.call_args_list[1][0][0]
        self.assertEqual(fail_call["eventType"], "CUSTOM_ERROR")
        self.assertEqual(fail_call["title"], "Function Failed: failing_function")
        self.assertEqual(fail_call["properties"]["status"], "FAILURE")
        self.assertEqual(fail_call["properties"]["error_message"], "Test error")
        
        mock_print.assert_called_with("Function failing_function failed with error: Test error")

    @patch('src.connectors.dynatrace_client.DynatraceClient.__init__', return_value=None)
    @patch.object(DynatraceClient, 'send_event')
    def test_trace_function_no_args(self, mock_send_event, mock_init):
        """Test trace function decorator with no arguments"""
        @trace_function
        def no_args_function():
            return "result"
        
        result = no_args_function()
        
        self.assertEqual(result, "result")
        
        # Check that repo_name defaults to 'N/A'
        start_call = mock_send_event.call_args_list[0][0][0]
        self.assertEqual(start_call["properties"]["application"], "N/A")


if __name__ == '__main__':
    unittest.main()
