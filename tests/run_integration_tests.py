#!/usr/bin/env python3
"""
Simple test runner script to test integration functionality
"""
import sys
import os
import unittest
from unittest.mock import patch, MagicMock
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Test basic integration functionality
def test_basic_integration():
    """Test basic integration components"""
    print("Testing basic integration...")
    
    # Test 1: Import main modules
    try:
        import main
        print("✓ Successfully imported main module")
    except Exception as e:
        print(f"✗ Failed to import main module: {e}")
        return False
    
    # Test 2: Test suggestion handler with mock data
    try:
        test_config = {
            'features': {
                'enable_ai_shadow_analyst': False
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
        
        with patch('main.load_config', return_value=test_config):
            event = {
                'body': json.dumps({
                    'suggestion_type': 'kubernetes_scaling',
                    'application': {
                        'name': 'test-app',
                        'version': '1.0.0',
                        'team': 'platform'
                    },
                    'deployment_context': {
                        'environment': 'prod',
                        'deployment_name': 'test-app',
                        'architecture': 'amd64'
                    }
                })
            }
            
            response = main.suggestion_handler(event, {})
            
            if response['statusCode'] == 200:
                response_body = json.loads(response['body'])
                if response_body['suggestion_source'] == 'static':
                    print("✓ Suggestion handler working correctly")
                else:
                    print("✗ Suggestion handler returned unexpected source")
                    return False
            else:
                print(f"✗ Suggestion handler returned error: {response}")
                return False
    except Exception as e:
        print(f"✗ Suggestion handler test failed: {e}")
        return False
    
    # Test 3: Test gate handler with mock data
    try:
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
        
        with patch('main.load_config', return_value=test_config):
            with patch('connectors.sonarqube_client.get_quality_gate_status') as mock_sonar:
                with patch('connectors.wiz_client.get_cve_status') as mock_wiz:
                    with patch('connectors.dynatrace_client.send_event') as mock_dynatrace:
                        
                        mock_sonar.return_value = {
                            'status': 'SUCCESS',
                            'message': 'All quality checks passed'
                        }
                        mock_wiz.return_value = {
                            'status': 'SUCCESS',
                            'message': 'No CVEs found'
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
                        
                        response = main.gate_handler(event, {})
                        
                        if response['statusCode'] == 200:
                            response_body = json.loads(response['body'])
                            if response_body['status'] == 'SUCCESS':
                                print("✓ Gate handler working correctly")
                            else:
                                print(f"✗ Gate handler returned unexpected status: {response_body}")
                                return False
                        else:
                            print(f"✗ Gate handler returned error: {response}")
                            return False
    except Exception as e:
        print(f"✗ Gate handler test failed: {e}")
        return False
    
    return True

def test_mcp_clients():
    """Test MCP client functionality"""
    print("\nTesting MCP clients...")
    
    # Test Mock MCP Client
    try:
        from mcp_client import MockMCPClient
        client = MockMCPClient()
        
        # Test performance metrics
        metrics = client.get_performance_metrics('test-service:prod')
        if 'cpu_usage_millicores_p90' in metrics:
            print("✓ Mock MCP client performance metrics working")
        else:
            print("✗ Mock MCP client performance metrics failed")
            return False
        
        # Test health events
        health = client.get_health_events('test-service:prod')
        if 'active_problem_count' in health:
            print("✓ Mock MCP client health events working")
        else:
            print("✗ Mock MCP client health events failed")
            return False
    except Exception as e:
        print(f"✗ Mock MCP client test failed: {e}")
        return False
    
    # Test Dynatrace MCP Client (with mocked requests)
    try:
        from mcp_client.dynatrace_mcp_client import DynatraceMCPClient
        
        with patch.dict(os.environ, {
            'DYNATRACE_API_URL': 'https://test.dynatrace.com',
            'DYNATRACE_API_TOKEN': 'test_token'
        }):
            with patch('requests.get') as mock_get:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.raise_for_status = MagicMock()
                mock_response.json.return_value = {
                    'result': [
                        {
                            'metricId': 'builtin:container.cpu.usage.millicores:percentile(90)',
                            'data': [{'values': [800]}]
                        }
                    ]
                }
                mock_get.return_value = mock_response
                
                client = DynatraceMCPClient()
                metrics = client.get_performance_metrics('test-service:prod')
                
                if metrics.get('cpu_usage_millicores_p90') == 800:
                    print("✓ Dynatrace MCP client working correctly")
                else:
                    print("✗ Dynatrace MCP client returned unexpected data")
                    return False
    except Exception as e:
        print(f"✗ Dynatrace MCP client test failed: {e}")
        return False
    
    return True

def test_llm_clients():
    """Test LLM client functionality"""
    print("\nTesting LLM clients...")
    
    # Test Ollama Client
    try:
        from llm_client.ollama_client import OllamaClient
        
        with patch.dict(os.environ, {
            'OLLAMA_API_ENDPOINT': 'http://localhost:11434/api/chat',
            'OLLAMA_MODEL': 'codellama:13b'
        }):
            with patch('urllib.request.urlopen') as mock_urlopen:
                mock_response = {
                    'message': {
                        'role': 'assistant',
                        'content': 'Test response',
                        'tool_calls': []
                    }
                }
                
                mock_http_response = MagicMock()
                mock_http_response.read.return_value = json.dumps(mock_response).encode('utf-8')
                mock_http_response.__enter__ = MagicMock(return_value=mock_http_response)
                mock_http_response.__exit__ = MagicMock(return_value=None)
                mock_urlopen.return_value = mock_http_response
                
                client = OllamaClient()
                response = client.call([{'role': 'user', 'content': 'Test'}])
                
                if response.get('role') == 'assistant':
                    print("✓ Ollama client working correctly")
                else:
                    print("✗ Ollama client returned unexpected response")
                    return False
    except Exception as e:
        print(f"✗ Ollama client test failed: {e}")
        return False
    
    # Test BYO LLM Client
    try:
        from llm_client.bring_your_own_llm_client import BringYourOwnLLMClient
        
        with patch('requests.post') as mock_post:
            mock_response = {
                'choices': [{
                    'message': {
                        'role': 'assistant',
                        'content': 'Test response',
                        'tool_calls': []
                    }
                }]
            }
            
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_response
            
            client = BringYourOwnLLMClient(
                api_key='test_key',
                api_endpoint='https://api.example.com/v1/chat'
            )
            
            response = client.call([{'role': 'user', 'content': 'Test'}])
            
            if response.get('role') == 'assistant':
                print("✓ BYO LLM client working correctly")
            else:
                print("✗ BYO LLM client returned unexpected response")
                return False
    except Exception as e:
        print(f"✗ BYO LLM client test failed: {e}")
        return False
    
    return True

def test_scaling_engine():
    """Test scaling engine functionality"""
    print("\nTesting scaling engine...")
    
    try:
        from suggestion_engines.scaling_engine import get_suggestion
        
        test_config = {
            'features': {
                'enable_ai_shadow_analyst': False
            },
            'scaling_suggestions': {
                'environments': {
                    'prod': {
                        'hpa': {
                            'min_replicas': 3,
                            'max_replicas': 15,
                            'cpu_utilization_target': 80
                        },
                        'karpenter': {
                            'capacity_type': 'on-demand'
                        }
                    }
                }
            }
        }
        
        app_context = {'name': 'test-service'}
        deployment_context = {
            'environment': 'prod',
            'deployment_name': 'test-service',
            'architecture': 'amd64'
        }
        
        result = get_suggestion(test_config, app_context, deployment_context)
        
        if result['suggestion_source'] == 'static':
            if result['suggestion']['hpa']['minReplicas'] == 3:
                print("✓ Scaling engine working correctly")
            else:
                print("✗ Scaling engine returned unexpected values")
                return False
        else:
            print("✗ Scaling engine returned unexpected source")
            return False
    except Exception as e:
        print(f"✗ Scaling engine test failed: {e}")
        return False
    
    return True

def main():
    """Run all integration tests"""
    print("Running SRE Agent Integration Tests")
    print("=" * 50)
    
    tests = [
        test_basic_integration,
        test_mcp_clients,
        test_llm_clients,
        test_scaling_engine
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ Test {test.__name__} failed with exception: {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All integration tests passed!")
        return 0
    else:
        print("❌ Some integration tests failed!")
        return 1

if __name__ == '__main__':
    sys.exit(main())
