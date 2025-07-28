import pytest
import json
import os
from unittest.mock import patch, MagicMock


from src.main import suggestion_handler, gate_handler
from src.suggestion_engines import scaling_engine
from src.mcp_client.dynatrace_mcp_client import DynatraceMCPClient
from src.mcp_client.mock_mcp_client import MockMCPClient
from src.llm_client.ollama_client import OllamaClient
from src.llm_client.bring_your_own_llm_client import BringYourOwnLLMClient


class TestBasicIntegration:
    """Basic integration tests for the SRE Agent."""
    
    def test_end_to_end_scaling_suggestion_with_mock_clients(self):
        """Test end-to-end scaling suggestion flow with mock clients."""
        # Setup test configuration
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
        
        # Mock the config loading
        with patch('src.main.load_config', return_value=test_config):
            # Mock environment variables for client selection
            with patch.dict(os.environ, {
                'MCP_CLIENT_TYPE': 'mock',
                'LLM_CLIENT_TYPE': 'ollama',
                'OLLAMA_API_ENDPOINT': 'http://localhost:11434/api/chat'
            }):
                # Mock the Ollama client response
                mock_ollama_response = {
                    'tool_calls': [{
                        'id': 'test_call_1',
                        'function': {
                            'name': 'submit_scaling_suggestion',
                            'arguments': json.dumps({
                                'hpa': {
                                    'minReplicas': 3,
                                    'maxReplicas': 12,
                                    'targetCPUUtilizationPercentage': 75,
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
                            })
                        }
                    }]
                }
                
                with patch('src.llm_client.ollama_client.OllamaClient.call', return_value=mock_ollama_response):
                    with patch('src.main._check_data_availability', return_value=('no_historical_data', None)):
                        with patch('src.suggestion_engines.scaling_engine._get_mcp_client') as mock_mcp:
                            mock_mcp.return_value.check_data_availability.return_value = ('no_historical_data', None)
                    # Create test event
                    event = {
                        'body': json.dumps({
                            'suggestion_type': 'kubernetes_scaling',
                                                'application': {
                        'name': 'test-app',
                        'namespace': 'test-app-prod',
                        'version': '1.0.0',
                        'team': 'platform'
                    },
                    'deployment_context': {
                        'environment': 'prod',
                        'deployment_name': 'test-app',
                        'architecture': 'amd64',
                        'cluster_name': 'eks-prod'
                    }
                        })
                    }
                    
                    # Execute the suggestion handler
                    response = suggestion_handler(event, {})
                    
                    # Verify response
                    assert response['statusCode'] == 200
                    response_body = json.loads(response['body'])
                    
                    # Verify AI suggestion was used
                    assert response_body['suggestion_source'] in ['llm_validated', 'ai_powered', 'ai_powered_with_fallbacks']
                    assert response_body['suggestion']['hpa']['minReplicas'] == 3
                    assert response_body['suggestion']['hpa']['maxReplicas'] == 12
                    assert response_body['suggestion']['hpa']['targetCPUUtilizationPercentage'] == 75

    def test_end_to_end_scaling_suggestion_fallback_to_static(self):
        """Test end-to-end scaling suggestion flow with fallback to static config."""
        # Setup test configuration
        test_config = {
            'features': {
                'enable_ai_shadow_analyst': False  # Disable AI to test static fallback
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
        
        # Create test event
        event = {
            'body': json.dumps({
                'suggestion_type': 'kubernetes_scaling',
                'application': {
                    'name': 'test-app',
                    'namespace': 'test-app-prod',
                    'version': '1.0.0',
                    'team': 'platform'
                },
                'deployment_context': {
                    'environment': 'prod',
                    'deployment_name': 'test-app',
                    'architecture': 'amd64',
                    'cluster_name': 'eks-prod'
                }
            })
        }
        
        # Mock the config loading
        with patch('src.main.load_config', return_value=test_config):
            with patch('src.main._check_data_availability', return_value=('no_historical_data', None)):
                with patch('src.suggestion_engines.scaling_engine._get_mcp_client') as mock_mcp:
                    mock_mcp.return_value.check_data_availability.return_value = ('no_historical_data', None)
                    with patch('src.suggestion_engines.scaling_engine.get_suggestion') as mock_get_suggestion:
                        mock_get_suggestion.return_value = {
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
                        
                        # Execute the suggestion handler
                        response = suggestion_handler(event, {})
                        
                        # Verify response
                        assert response['statusCode'] == 200
                        response_body = json.loads(response['body'])
                        
                        # Verify static suggestion was used
                        assert response_body['suggestion_source'] in ['static', 'ai_powered_with_fallbacks']
                        assert 'suggestion' in response_body
                        assert 'hpa' in response_body['suggestion']
                        assert response_body['suggestion']['hpa']['minReplicas'] == 2
                        assert response_body['suggestion']['hpa']['maxReplicas'] == 10  # Should match the mock response
                        assert response_body['suggestion']['hpa']['targetCPUUtilizationPercentage'] == 70

    def test_dynatrace_mcp_integration(self):
        """Test integration with Dynatrace MCP server."""
        # Mock Dynatrace API responses
        mock_metrics_response = {
            'result': [
                {
                    'metricId': 'builtin:container.cpu.usage.millicores:percentile(90)',
                    'data': [{'values': [800]}]
                },
                {
                    'metricId': 'builtin:container.memory.workingSet.bytes:percentile(90)',
                    'data': [{'values': [1073741824]}]  # 1GB
                },
                {
                    'metricId': 'builtin:container.cpu.requests',
                    'data': [{'values': [500]}]
                },
                {
                    'metricId': 'builtin:container.memory.requests',
                    'data': [{'values': [536870912]}]  # 512MB
                }
            ]
        }
        
        mock_problems_response = {
            'problems': [
                {'title': 'High CPU usage', 'severityLevel': 'WARNING'}
            ]
        }
        
        mock_events_response = {
            'totalCount': 2
        }
        
        with patch.dict(os.environ, {
            'DYNATRACE_API_URL': 'https://test.dynatrace.com',
            'DYNATRACE_API_TOKEN': 'test_token'
        }):
            with patch('src.utils.secrets_manager.get_secret_value', side_effect=lambda x: os.environ.get(x)):
                with patch('requests.get') as mock_get:
                    
                    def mock_get_response(url, **kwargs):
                        mock_resp = MagicMock()
                        mock_resp.status_code = 200
                        
                        if 'metrics/query' in url:
                            mock_resp.json.return_value = mock_metrics_response
                        elif 'problems' in url:
                            mock_resp.json.return_value = mock_problems_response
                        elif 'events' in url:
                            mock_resp.json.return_value = mock_events_response
                        
                        return mock_resp
                    
                    mock_get.side_effect = mock_get_response
                    
                    # Test MCP client
                    client = DynatraceMCPClient()
                    
                    # Test metrics retrieval
                    metrics = client.get_performance_metrics('test-service:prod')
                    
                    # Verify metrics were retrieved and processed
                    assert 'cpu_usage_millicores_p90' in metrics
                    assert metrics['cpu_usage_millicores_p90'] == 800
                    assert metrics['memory_usage_mb_p90'] == 1024.0
                    assert metrics['pod_cpu_requests_millicores'] == 500
                    assert metrics['pod_memory_requests_mb'] == 512.0
                    
                    # Test health events retrieval
                    health = client.get_health_events('test-service:prod')
                    
                    # Verify health events were retrieved
                    assert health['active_problem_count'] == 1
                    assert len(health['active_problems']) == 1
                    assert health['active_problems'][0]['title'] == 'High CPU usage'
                    assert health['recent_oom_kills'] == 2

    def test_ollama_llm_integration(self):
        """Test integration with Ollama LLM client."""
        with patch.dict(os.environ, {
            'OLLAMA_API_ENDPOINT': 'http://localhost:11434/api/chat'
        }):
            mock_response = {
                'message': {
                    'role': 'assistant',
                    'content': 'Analysis complete.',
                    'tool_calls': [{
                        'id': 'test_call_1',
                        'function': {
                            'name': 'get_performance_metrics',
                            'arguments': '{"entity_id": "test-service:prod"}'
                        }
                    }]
                }
            }
            
            with patch('urllib.request.urlopen') as mock_urlopen:
                mock_response_obj = MagicMock()
                mock_response_obj.read.return_value = json.dumps(mock_response).encode('utf-8')
                mock_response_obj.status = 200
                mock_urlopen.return_value.__enter__.return_value = mock_response_obj
                
                # Test Ollama client
                client = OllamaClient()
                
                messages = [
                    {'role': 'user', 'content': 'Analyze the performance metrics for test-service:prod'}
                ]
                
                tools = [
                    {
                        'type': 'function',
                        'function': {
                            'name': 'get_performance_metrics',
                            'description': 'Gets performance metrics',
                            'parameters': {
                                'type': 'object',
                                'properties': {
                                    'entity_id': {'type': 'string'}
                                },
                                'required': ['entity_id']
                            }
                        }
                    }
                ]
                
                response = client.call(messages, tools)
                
                # Verify response
                assert response['role'] == 'assistant'
                assert 'tool_calls' in response
                assert len(response['tool_calls']) == 1
                assert response['tool_calls'][0]['function']['name'] == 'get_performance_metrics'
                
                # Verify the request was made correctly
                mock_urlopen.assert_called_once()
                call_args = mock_urlopen.call_args
                request = call_args[0][0]
                assert request.get_method() == 'POST'
                assert 'localhost:11434' in request.full_url

    def test_quality_gate_integration(self):
        """Test quality gate integration with multiple connectors."""
        test_config = {
            'gating_rules': {
                'weights': {
                    'sonarqube': 40,
                    'wiz': 30,
                    'tests': 30
                },
                'promotion_threshold': 90
            }
        }
        
        with patch('src.main.load_config', return_value=test_config):
            # Mock successful quality checks
            with patch('src.utils.secrets_manager.get_secret_value', return_value='test_value'):
                with patch('src.connectors.dynatrace_client.DynatraceClient') as mock_dynatrace_class:
                    with patch('src.connectors.slack_client.SlackClient') as mock_slack_class:
                        with patch('src.main._run_quality_checks') as mock_quality_checks:
                            
                            # Mock client instances
                            mock_dynatrace_instance = MagicMock()
                            mock_dynatrace_class.return_value = mock_dynatrace_instance
                            mock_slack_instance = MagicMock()
                            mock_slack_class.return_value = mock_slack_instance
                            
                            # Mock successful quality checks
                            mock_quality_checks.return_value = {
                                'sonarqube': {'status': 'SUCCESS', 'message': 'All quality checks passed'},
                                'wiz': {'status': 'SUCCESS', 'message': 'No CVEs found'}
                            }

                            event = {
                                'body': json.dumps({
                                    'application': {
                                        'name': 'test-app',
                                        'commit_sha': 'abc123',
                                        'artifact_id': 'test-app:v1.0.0'
                                    }
                                })
                            }
                        
                            response = gate_handler(event, {})
                            
                            # Verify successful response
                            assert response['statusCode'] == 200
                            response_body = json.loads(response['body'])
                            
                            assert response_body['status'] == 'SUCCESS'
                            assert response_body['score'] == 100
                            assert 'All quality gates passed' in response_body['message']
                            
                            # Verify Dynatrace event was sent
                            mock_dynatrace_instance.send_event.assert_called_once()

    def test_quality_gate_failure_integration(self):
        """Test quality gate failure scenario."""
        test_config = {
            'gating_rules': {
                'weights': {
                    'sonarqube': 40,
                    'wiz': 30,
                    'tests': 30
                },
                'promotion_threshold': 90
            }
        }
        
        with patch('src.main.load_config', return_value=test_config):
            # Mock failed quality checks
            with patch('src.utils.secrets_manager.get_secret_value', return_value='test_value'):
                with patch('src.connectors.dynatrace_client.DynatraceClient') as mock_dynatrace_class:
                    with patch('src.connectors.slack_client.SlackClient') as mock_slack_class:
                        with patch('src.main._run_quality_checks') as mock_quality_checks:
                            
                            # Mock client instances
                            mock_dynatrace_instance = MagicMock()
                            mock_dynatrace_class.return_value = mock_dynatrace_instance
                            mock_slack_instance = MagicMock()
                            mock_slack_class.return_value = mock_slack_instance
                            
                            # Mock failed quality checks
                            mock_quality_checks.return_value = {
                                'sonarqube': {'status': 'FAILURE', 'message': 'Code coverage below threshold'},
                                'wiz': {'status': 'FAILURE', 'message': 'Critical CVEs found'}
                            }
                            
                            event = {
                                'body': json.dumps({
                                    'application': {
                                        'name': 'test-app',
                                        'commit_sha': 'abc123',
                                        'artifact_id': 'test-app:v1.0.0'
                                    }
                                })
                            }
                            
                            response = gate_handler(event, {})
                            
                            # Verify failure response
                            assert response['statusCode'] == 200
                            response_body = json.loads(response['body'])
                            
                            assert response_body['status'] == 'FAILURE'
                            assert response_body['score'] == 30
                            assert 'Quality gate failed' in response_body['message']
                            assert len(response_body['issues']) == 2
                            
                            # Verify notifications were sent
                            mock_dynatrace_instance.send_event.assert_called_once()
                            mock_slack_instance.send_notification.assert_called_once()

    def test_bring_your_own_llm_integration(self):
        """Test integration with bring-your-own LLM client."""
        with patch.dict(os.environ, {
            'LLM_CLIENT_TYPE': 'byo',
            'BYO_LLM_API_KEY': 'test_api_key',
            'BYO_LLM_API_ENDPOINT': 'https://api.example.com/v1/chat'
        }):
            mock_response = {
                'choices': [{
                    'message': {
                        'role': 'assistant',
                        'content': 'Analysis complete.',
                        'tool_calls': [{
                            'id': 'test_call_1',
                            'function': {
                                'name': 'get_performance_metrics',
                                'arguments': '{"entity_id": "test-service:prod"}'
                            }
                        }]
                    }
                }]
            }
            
            with patch('urllib.request.urlopen') as mock_urlopen:
                mock_response_obj = MagicMock()
                mock_response_obj.read.return_value = json.dumps(mock_response).encode('utf-8')
                mock_response_obj.status = 200
                mock_urlopen.return_value.__enter__.return_value = mock_response_obj
                
                client = BringYourOwnLLMClient(
                    api_key='test_api_key',
                    api_endpoint='https://api.example.com/v1/chat'
                )
                
                messages = [
                    {'role': 'user', 'content': 'Analyze metrics'}
                ]
                
                response = client.call(messages)
                
                # Verify response - BYO client returns full response, need to extract message
                assert 'choices' in response
                assert len(response['choices']) == 1
                message = response['choices'][0]['message']
                assert message['role'] == 'assistant'
                assert 'tool_calls' in message
                assert len(message['tool_calls']) == 1
                
                # Verify request was made correctly
                mock_urlopen.assert_called_once()
