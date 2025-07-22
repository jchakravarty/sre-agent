import unittest
import sys
import os
from unittest.mock import patch, MagicMock
import requests

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Import using direct path
import importlib.util
module_path = os.path.join(os.path.dirname(__file__), '..', '..', 'examples', 'harness-integration', 'harness_integration_example.py')
spec = importlib.util.spec_from_file_location("harness_integration_example", module_path)

if spec is None or spec.loader is None:
    raise ImportError(f"Could not load module from {module_path}")

harness_integration_example = importlib.util.module_from_spec(spec)
spec.loader.exec_module(harness_integration_example)
HarnessIntegration = harness_integration_example.HarnessIntegration

class TestHarnessIntegration(unittest.TestCase):

    @patch('requests.post')
    def test_get_scaling_suggestion(self, mock_post):
        # Mock the response from the SRE Agent
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'suggestion_source': 'llm_validated',
            'suggestion': {
                'hpa': {
                    'minReplicas': 1,
                    'maxReplicas': 5,
                    'targetCPUUtilizationPercentage': 75,
                    'scaleTargetRefName': 'test-deploy',
                    'resources': {
                        'cpuLimit': '1',
                        'memoryLimit': '1Gi',
                        'cpuRequest': '500m',
                        'memoryRequest': '512Mi'
                    }
                },
                'karpenter': {
                    'kubernetes.io/arch': 'amd64',
                    'karpenter.sh/capacity-type': 'spot'
                }
            }
        }
        mock_post.return_value = mock_response

        harness = HarnessIntegration('http://mock-sre-agent')
        suggestion = harness.get_scaling_suggestion('test-app', 'prod', 'test-deploy')

        self.assertEqual(suggestion['suggestion_source'], 'llm_validated')
        self.assertEqual(suggestion['suggestion']['hpa']['minReplicas'], 1)
        self.assertEqual(suggestion['suggestion']['hpa']['resources']['cpuLimit'], '1')

    @patch('requests.post')
    def test_check_quality_gate(self, mock_post):
        # Mock the response from the SRE Agent
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 'SUCCESS',
            'message': 'All quality gates passed',
            'score': 95
        }
        mock_post.return_value = mock_response

        harness = HarnessIntegration('http://mock-sre-agent')
        result = harness.check_quality_gate('test-app', 'abc123', 'artifact:v1.0.0')

        self.assertEqual(result['status'], 'SUCCESS')
        self.assertEqual(result['score'], 95)

if __name__ == '__main__':
    unittest.main()
