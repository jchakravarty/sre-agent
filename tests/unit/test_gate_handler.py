import unittest
from unittest.mock import patch, MagicMock
import json
from src import main

class TestGateHandler(unittest.TestCase):

    @patch('src.main.load_config')
    @patch('src.main._run_quality_checks')
    @patch('src.main.dynatrace_client.DynatraceClient')
    @patch('src.main.slack_client.SlackClient')
    def test_gate_pass(self, mock_slack_class, mock_dynatrace_class, mock_checks, mock_config):
        """
        Test that the gate passes when all checks are successful.
        """
        # Mock the client instances
        mock_dynatrace_instance = MagicMock()
        mock_dynatrace_class.return_value = mock_dynatrace_instance
        mock_slack_instance = MagicMock()
        mock_slack_class.return_value = mock_slack_instance
        
        # Mock configuration
        mock_config.return_value = {
            "gating_rules": {
                "weights": {"sonarqube": 50, "wiz": 40, "tests": 10},
                "promotion_threshold": 90
            }
        }
        # Mock successful checks
        mock_checks.return_value = {
            "sonarqube": {"status": "SUCCESS"},
            "wiz": {"status": "SUCCESS"}
        }
        
        event = {
            'body': json.dumps({
                "application": {"name": "test-app", "commit_sha": "abc", "artifact_id": "123"},
            })
        }
        
        response = main.gate_handler(event, None)
        
        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertEqual(body['status'], 'SUCCESS')
        self.assertEqual(body['score'], 100)
        mock_dynatrace_instance.send_event.assert_called_once()
        mock_slack_instance.send_notification.assert_not_called()

    @patch('src.main.load_config')
    @patch('src.main._run_quality_checks')
    @patch('src.main.dynatrace_client.DynatraceClient')
    @patch('src.main.slack_client.SlackClient')
    def test_gate_fail_on_score(self, mock_slack_class, mock_dynatrace_class, mock_checks, mock_config):
        """
        Test that the gate fails when the score is below the threshold.
        """
        # Mock the client instances
        mock_dynatrace_instance = MagicMock()
        mock_dynatrace_class.return_value = mock_dynatrace_instance
        mock_slack_instance = MagicMock()
        mock_slack_class.return_value = mock_slack_instance
        
        mock_config.return_value = {
            "gating_rules": {
                "weights": {"sonarqube": 50, "wiz": 40, "tests": 10},
                "promotion_threshold": 90
            }
        }
        # Mock a failed check
        mock_checks.return_value = {
            "sonarqube": {"status": "SUCCESS"},
            "wiz": {"status": "FAILURE", "message": "Critical CVE found"}
        }
        
        event = {
            'body': json.dumps({
                "application": {"name": "test-app", "commit_sha": "abc", "artifact_id": "123"},
            })
        }
        
        response = main.gate_handler(event, None)
        
        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertEqual(body['status'], 'FAILURE')
        self.assertEqual(body['score'], 60) # 50 for sonar + 10 for tests
        self.assertIn("Wiz failed: Critical CVE found", body['issues'])
        mock_dynatrace_instance.send_event.assert_called_once()
        mock_slack_instance.send_notification.assert_called_once()

if __name__ == '__main__':
    unittest.main()
