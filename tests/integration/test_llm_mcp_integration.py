import pytest
import json
import os
from unittest.mock import patch, MagicMock
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from src.suggestion_engines.scaling_engine import get_suggestion, _get_llm_client, _get_mcp_client
from src.mcp_client.dynatrace_mcp_client import DynatraceMCPClient
from src.mcp_client.mock_mcp_client import MockMCPClient
from src.llm_client.ollama_client import OllamaClient
from src.llm_client.bring_your_own_llm_client import BringYourOwnLLMClient


class TestLLMMCPIntegration:
    """Integration tests for LLM and MCP client workflows."""
    
    def test_llm_mcp_orchestration_flow(self):
        """Test the complete LLM-MCP orchestration flow."""
        test_config = {
            'features': {
                'enable_ai_shadow_analyst': True
            },
            'scaling_suggestions': {
                'environments': {
                    'prod': {
                        'hpa': {
                            'min_replicas': 2,
                            'max_replicas': 10,
                            'cpu_utilization_target': 70
                        },
                        'karpenter': {
                            'capacity_type': 'spot'
                        }
                    }
                }
            }
        }
        
        app_context = {
            'name': 'test-service',
            'version': '1.0.0',
            'team': 'platform'
        }
        
        deployment_context = {
            'environment': 'prod',
            'deployment_name': 'test-service',
            'architecture': 'amd64',
            'cluster_name': 'eks-prod',
            'namespace': 'test-service-prod'
        }
        
        with patch.dict(os.environ, {
            'MCP_CLIENT_TYPE': 'dynatrace',
            'LLM_CLIENT_TYPE': 'ollama',
            'DYNATRACE_API_URL': 'https://test.dynatrace.com',
            'DYNATRACE_API_TOKEN': 'test_token',
            'OLLAMA_API_ENDPOINT': 'http://localhost:11434/api/chat'
        }):
            # Mock Dynatrace API responses
            mock_metrics_response = {
                'result': [
                    {
                        'metricId': 'builtin:container.cpu.usage.millicores:percentile(90)',
                        'data': [{'values': [1200]}]  # High CPU usage
                    },
                    {
                        'metricId': 'builtin:container.memory.workingSet.bytes:percentile(90)',
                        'data': [{'values': [1610612736]}]  # 1.5GB memory usage
                    }
                ]
            }
            
            # Mock LLM responses for the conversation flow
            llm_responses = [
                # First response: LLM calls get_performance_metrics
                {
                    'role': 'assistant',
                    'content': 'I need to analyze the performance metrics first.',
                    'tool_calls': [{
                        'id': 'call_1',
                        'function': {
                            'name': 'get_performance_metrics',
                            'arguments': '{"entity_id": "test-service:prod"}'
                        }
                    }]
                },
                # Second response: LLM calls get_health_events
                {
                    'role': 'assistant',
                    'content': 'Now let me check for health events.',
                    'tool_calls': [{
                        'id': 'call_2',
                        'function': {
                            'name': 'get_health_events',
                            'arguments': '{"entity_id": "test-service:prod"}'
                        }
                    }]
                },
                # Third response: LLM submits scaling suggestion
                {
                    'role': 'assistant',
                    'content': 'Based on the metrics, I recommend scaling up.',
                    'tool_calls': [{
                        'id': 'call_3',
                        'function': {
                            'name': 'submit_scaling_suggestion',
                            'arguments': json.dumps({
                                'hpa': {
                                    'minReplicas': 4,
                                    'maxReplicas': 20,
                                    'targetCPUUtilizationPercentage': 65,
                                    'scaleTargetRefName': 'test-service',
                                    'resources': {
                                        'cpuLimit': '2000m',
                                        'memoryLimit': '2Gi',
                                        'cpuRequest': '1000m',
                                        'memoryRequest': '1Gi'
                                    }
                                },
                                'karpenter': {
                                    'kubernetes.io/arch': 'amd64',
                                    'karpenter.sh/capacity-type': 'spot'
                                }
                            })
                        }
                    }]
                }
            ]
            
            with patch('requests.get') as mock_get:
                with patch('urllib.request.urlopen') as mock_urlopen:
                    # Mock Dynatrace API calls
                    mock_response = MagicMock()
                    mock_response.status_code = 200
                    mock_response.raise_for_status = MagicMock()
                    mock_response.json.return_value = mock_metrics_response
                    mock_get.return_value = mock_response
                    
                    # Mock Ollama API calls
                    call_count = 0
                    def mock_ollama_response(*args, **kwargs):
                        nonlocal call_count
                        mock_http_response = MagicMock()
                        response_data = {'message': llm_responses[call_count]}
                        mock_http_response.read.return_value = json.dumps(response_data).encode('utf-8')
                        mock_http_response.__enter__ = MagicMock(return_value=mock_http_response)
                        mock_http_response.__exit__ = MagicMock(return_value=None)
                        call_count += 1
                        return mock_http_response
                    
                    mock_urlopen.side_effect = mock_ollama_response
                    
                    # Execute the scaling suggestion
                    result = get_suggestion(test_config, app_context, deployment_context)
                    
                    # Verify AI suggestion was used
                    assert result['suggestion_source'] == 'llm_validated'
                    assert result['suggestion']['hpa']['minReplicas'] == 4
                    assert result['suggestion']['hpa']['maxReplicas'] == 20
                    assert result['suggestion']['hpa']['targetCPUUtilizationPercentage'] == 65
                    
                    # Verify multiple tool calls were made
                    assert mock_urlopen.call_count == 3
                    assert mock_get.call_count >= 1  # Dynatrace API calls
    
    def test_mcp_client_factory_selection(self):
        """Test MCP client factory selection based on environment."""
        # Test Dynatrace MCP client selection
        with patch.dict(os.environ, {
            'MCP_CLIENT_TYPE': 'dynatrace',
            'DYNATRACE_API_URL': 'https://test.dynatrace.com',
            'DYNATRACE_API_TOKEN': 'test_token'
        }):
            client = _get_mcp_client()
            assert isinstance(client, DynatraceMCPClient)
        
        # Test Mock MCP client selection
        with patch.dict(os.environ, {'MCP_CLIENT_TYPE': 'mock'}):
            client = _get_mcp_client()
            assert isinstance(client, MockMCPClient)
        
        # Test default selection (should be Dynatrace)
        with patch.dict(os.environ, {
            'DYNATRACE_API_URL': 'https://test.dynatrace.com',
            'DYNATRACE_API_TOKEN': 'test_token'
        }):
            with patch.dict(os.environ, {'MCP_CLIENT_TYPE': ''}, clear=False):
                client = _get_mcp_client()
                assert isinstance(client, DynatraceMCPClient)
    
    def test_llm_client_factory_selection(self):
        """Test LLM client factory selection based on environment."""
        # Test Ollama client selection
        with patch.dict(os.environ, {
            'LLM_CLIENT_TYPE': 'ollama',
            'OLLAMA_API_ENDPOINT': 'http://localhost:11434/api/chat'
        }):
            client = _get_llm_client()
            assert isinstance(client, OllamaClient)
        
        # Test BYO LLM client selection
        with patch.dict(os.environ, {
            'LLM_CLIENT_TYPE': 'byo',
            'BYO_LLM_API_KEY': 'test_key',
            'BYO_LLM_API_ENDPOINT': 'https://api.example.com/v1/chat'
        }):
            client = _get_llm_client()
            assert isinstance(client, BringYourOwnLLMClient)
        
        # Test missing BYO configuration
        with patch.dict(os.environ, {
            'LLM_CLIENT_TYPE': 'byo',
            'BYO_LLM_API_KEY': '',
            'BYO_LLM_API_ENDPOINT': ''
        }):
            with pytest.raises(ValueError, match="BYO_LLM_API_KEY and BYO_LLM_API_ENDPOINT must be set"):
                _get_llm_client()
    
    def test_mock_mcp_client_integration(self):
        """Test integration with mock MCP client."""
        with patch.dict(os.environ, {'MCP_CLIENT_TYPE': 'mock'}):
            client = MockMCPClient()
            
            # Test performance metrics
            metrics = client.get_performance_metrics('test-service:prod')
            assert 'cpu_usage_millicores_p90' in metrics
            assert 'memory_usage_mb_p90' in metrics
            assert isinstance(metrics['cpu_usage_millicores_p90'], (int, float))
            
            # Test health events
            health = client.get_health_events('test-service:prod')
            assert 'active_problem_count' in health
            assert 'recent_oom_kills' in health
            assert isinstance(health['active_problem_count'], int)
            
            # Test SLOs
            slos = client.get_service_level_objectives('test-service:prod')
            assert isinstance(slos, list)
    
    def test_llm_tool_call_validation(self):
        """Test LLM tool call validation and error handling."""
        with patch.dict(os.environ, {
            'LLM_CLIENT_TYPE': 'ollama',
            'OLLAMA_API_ENDPOINT': 'http://localhost:11434/api/chat'
        }):
            # Test invalid tool call
            mock_response = {
                'message': {
                    'role': 'assistant',
                    'content': 'I will call an invalid tool.',
                    'tool_calls': [{
                        'id': 'call_1',
                        'function': {
                            'name': 'invalid_tool_name',
                            'arguments': '{"param": "value"}'
                        }
                    }]
                }
            }
            
            with patch('urllib.request.urlopen') as mock_urlopen:
                mock_http_response = MagicMock()
                mock_http_response.read.return_value = json.dumps(mock_response).encode('utf-8')
                mock_http_response.__enter__ = MagicMock(return_value=mock_http_response)
                mock_http_response.__exit__ = MagicMock(return_value=None)
                mock_urlopen.return_value = mock_http_response
                
                client = OllamaClient()
                response = client.call([{'role': 'user', 'content': 'Test'}])
                
                # Should still return response with tool call
                assert response['role'] == 'assistant'
                assert 'tool_calls' in response
                assert response['tool_calls'][0]['function']['name'] == 'invalid_tool_name'
    
    def test_scaling_suggestion_validation(self):
        """Test scaling suggestion validation."""
        # Test valid scaling suggestion
        valid_suggestion = {
            'hpa': {
                'minReplicas': 2,
                'maxReplicas': 10,
                'targetCPUUtilizationPercentage': 70,
                'scaleTargetRefName': 'test-app',
                'resources': {
                    'cpuLimit': '1000m',
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
        
        # Should not raise exception for valid suggestion
        from data_models import ScalingSuggestion
        validated = ScalingSuggestion.model_validate(valid_suggestion)
        assert validated.hpa.min_replicas == 2
        assert validated.hpa.max_replicas == 10
        
        # Test invalid scaling suggestion (max < min)
        invalid_suggestion = {
            'hpa': {
                'minReplicas': 10,
                'maxReplicas': 2,  # Invalid: max < min
                'targetCPUUtilizationPercentage': 70,
                'scaleTargetRefName': 'test-app',
                'resources': {
                    'cpuLimit': '1000m',
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
        
        # Should raise validation error
        with pytest.raises(ValueError, match="max_replicas must be greater than or equal to min_replicas"):
            ScalingSuggestion.model_validate(invalid_suggestion)
    
    def test_llm_conversation_timeout(self):
        """Test LLM conversation timeout handling."""
        test_config = {
            'features': {
                'enable_ai_shadow_analyst': True
            },
            'scaling_suggestions': {
                'environments': {
                    'prod': {
                        'hpa': {
                            'min_replicas': 2,
                            'max_replicas': 10,
                            'cpu_utilization_target': 70
                        }
                    }
                }
            }
        }
        
        app_context = {'name': 'test-service'}
        deployment_context = {'environment': 'prod', 'deployment_name': 'test-service'}
        
        with patch.dict(os.environ, {
            'LLM_CLIENT_TYPE': 'ollama',
            'OLLAMA_API_ENDPOINT': 'http://localhost:11434/api/chat'
        }):
            # Mock infinite loop scenario (LLM never calls submit_scaling_suggestion)
            mock_response = {
                'message': {
                    'role': 'assistant',
                    'content': 'Let me get more metrics.',
                    'tool_calls': [{
                        'id': 'call_1',
                        'function': {
                            'name': 'get_performance_metrics',
                            'arguments': '{"entity_id": "test-service:prod"}'
                        }
                    }]
                }
            }
            
            with patch('urllib.request.urlopen') as mock_urlopen:
                mock_http_response = MagicMock()
                mock_http_response.read.return_value = json.dumps(mock_response).encode('utf-8')
                mock_http_response.__enter__ = MagicMock(return_value=mock_http_response)
                mock_http_response.__exit__ = MagicMock(return_value=None)
                mock_urlopen.return_value = mock_http_response
                
                # Should fall back to static suggestion after max iterations
                result = get_suggestion(test_config, app_context, deployment_context)
                
                # Should use static fallback
                assert result['suggestion_source'] == 'static'
                assert result['suggestion']['hpa']['minReplicas'] == 2
                assert result['suggestion']['hpa']['maxReplicas'] == 10
                
                # Should have made exactly 5 calls (the limit)
                assert mock_urlopen.call_count == 5
