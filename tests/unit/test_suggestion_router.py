import unittest
from unittest.mock import patch, MagicMock
import json
from src import main

class TestSuggestionRouter(unittest.TestCase):

    @patch('src.main.load_config')
    @patch('src.main.suggestion_engines.scaling_engine')
    @patch('src.main._check_data_availability')
    def test_router_success_scaling(self, mock_data_availability, mock_scaling_engine, mock_config):
        """
        Test that the router successfully calls the scaling engine.
        """
        mock_config.return_value = {}
        mock_data_availability.return_value = ('no_historical_data', None)
        mock_scaling_engine.get_suggestion.return_value = {
            "suggestion": {
                "hpa": {
                    "minReplicas": 2,
                    "maxReplicas": 10,
                    "targetCPUUtilizationPercentage": 70,
                    "scaleTargetRefName": "test-app",
                    "resources": {
                        "cpuLimit": "1000m",
                        "memoryLimit": "1Gi",
                        "cpuRequest": "500m",
                        "memoryRequest": "512Mi"
                    }
                },
                "karpenter": {
                    "kubernetes.io/arch": "amd64",
                    "karpenter.sh/capacity-type": "spot"
                }
            },
            "suggestion_source": "static"
        }
        
        event = {
            'body': json.dumps({
                "suggestion_type": "kubernetes_scaling",
                "application": {"name": "test-app", "namespace": "test-namespace"},
                "deployment_context": {"environment": "dev"}
            })
        }
        
        response = main.suggestion_handler(event, None)
        
        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        # Check that the enhanced response structure is present
        self.assertIn('suggestion_source', body)
        self.assertIn('data_availability', body)
        self.assertIn('inferred_context', body)
        self.assertIn('suggestion', body)
        mock_scaling_engine.get_suggestion.assert_called_once()

    def test_router_missing_type(self):
        """
        Test that the router fails if suggestion_type is missing.
        """
        event = {'body': json.dumps({"application": {}})}
        response = main.suggestion_handler(event, None)
        self.assertEqual(response['statusCode'], 400)
        body = json.loads(response['body'])
        self.assertIn("Missing required key: suggestion_type", body['message'])

    def test_router_unknown_type(self):
        """
        Test that the router fails for an unknown suggestion_type.
        """
        event = {'body': json.dumps({"suggestion_type": "unknown_type"})}
        response = main.suggestion_handler(event, None)
        self.assertEqual(response['statusCode'], 400)
        body = json.loads(response['body'])
        self.assertIn("Unknown suggestion_type", body['message'])

if __name__ == '__main__':
    unittest.main()
