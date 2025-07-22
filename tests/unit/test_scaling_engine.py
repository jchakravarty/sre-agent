import unittest
from unittest.mock import patch, MagicMock
from src.suggestion_engines import scaling_engine

class TestScalingEngine(unittest.TestCase):

    @patch('src.suggestion_engines.scaling_engine._get_llm_client')
    @patch('src.suggestion_engines.scaling_engine._get_mcp_client')
    def test_static_suggestion_fallback(self, mock_get_mcp_client, mock_get_llm_client):
        """
        Test that the engine falls back to a static suggestion when the AI is disabled.
        """
        mock_get_llm_client.return_value = None
        
        config = {
            "features": {"enable_ai_shadow_analyst": False},
            "scaling_suggestions": {
                "environments": {
                    "dev": {"hpa": {"min_replicas": 1, "max_replicas": 5}}
                }
            }
        }
        app_context = {"name": "test-app"}
        deployment_context = {"environment": "dev", "deployment_name": "test-deploy", "architecture": "amd64"}
        
        result = scaling_engine.get_suggestion(config, app_context, deployment_context)
        
        self.assertEqual(result['suggestion_source'], 'static')
        self.assertEqual(result['suggestion']['hpa']['minReplicas'], 1)
        self.assertEqual(result['suggestion']['hpa']['maxReplicas'], 5)
        mock_get_llm_client.assert_not_called()

    @patch('src.suggestion_engines.scaling_engine._get_llm_client')
    @patch('src.suggestion_engines.scaling_engine._get_mcp_client')
    def test_ai_suggestion_success(self, mock_get_mcp_client, mock_get_llm_client):
        """
        Test that the engine uses the AI suggestion when it's valid.
        """
        mock_llm_client = MagicMock()
        mock_llm_client.call.return_value = {
            "tool_calls": [{
                "function": {
                    "name": "submit_scaling_suggestion",
                    "arguments": '{"hpa": {"minReplicas": 10, "maxReplicas": 20, "targetCPUUtilizationPercentage": 80, "scaleTargetRefName": "test-deploy", "resources": {"cpuLimit": "1", "memoryLimit": "1Gi", "cpuRequest": "500m", "memoryRequest": "512Mi"}}, "karpenter": {"kubernetes.io/arch": "amd64", "karpenter.sh/capacity-type": "spot"}}'
                }
            }]
        }
        mock_get_llm_client.return_value = mock_llm_client
        
        mock_mcp_client = MagicMock()
        mock_mcp_client.get_scaling_context.return_value = {}
        mock_get_mcp_client.return_value = mock_mcp_client
        
        config = {"features": {"enable_ai_shadow_analyst": True}}
        app_context = {"name": "test-app"}
        deployment_context = {"environment": "prod"}
        
        result = scaling_engine.get_suggestion(config, app_context, deployment_context)
        
        self.assertEqual(result['suggestion_source'], 'llm_validated')
        self.assertEqual(result['suggestion']['hpa']['minReplicas'], 10)
        self.assertEqual(result['suggestion']['hpa']['resources']['cpuLimit'], "1")
        mock_get_llm_client.assert_called_once()
        mock_llm_client.call.assert_called_once()
        mock_get_mcp_client.assert_called_once()
        mock_mcp_client.get_performance_metrics.assert_not_called()
        mock_mcp_client.get_health_events.assert_not_called()
        mock_mcp_client.get_service_level_objectives.assert_not_called()
        mock_mcp_client.get_health_events.assert_not_called()
        mock_mcp_client.get_service_level_objectives.assert_not_called()

if __name__ == '__main__':
    unittest.main()
