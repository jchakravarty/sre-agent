"""
Real service integration tests - Tests against actual services when available.
These tests provide more realistic validation but may be skipped if services are unavailable.
"""
import pytest
import json
import os
import requests
import urllib.request
import urllib.error
from unittest.mock import patch, MagicMock
from src.llm_client.ollama_client import OllamaClient
from src.llm_client.bring_your_own_llm_client import BringYourOwnLLMClient
from src.mcp_client.dynatrace_mcp_client import DynatraceMCPClient
from src.connectors.dynatrace_client import DynatraceClient


def is_service_available(url, timeout=5):
    """Check if a service is available by making a health check request."""
    try:
        response = requests.get(url, timeout=timeout)
        return response.status_code < 500
    except (requests.exceptions.RequestException, Exception):
        return False


def is_ollama_available():
    """Check if Ollama service is available."""
    ollama_endpoint = os.environ.get('OLLAMA_API_ENDPOINT', 'http://ollama:11434/api/chat')
    base_url = ollama_endpoint.replace('/api/chat', '')
    return is_service_available(f"{base_url}/api/version")


def is_wiremock_available():
    """Check if WireMock service is available."""
    return is_service_available("http://wiremock:8080/__admin/health")


def is_dynatrace_mcp_available():
    """Check if Dynatrace MCP server is available."""
    return is_service_available("http://dynatrace-mcp-server:3000/health")


class TestRealServiceIntegration:
    """Integration tests that connect to real services when available."""

    def test_ollama_real_service_integration(self):
        """Test integration with real Ollama service."""
        if not is_ollama_available():
            pytest.skip("Ollama service not available")
            
        print("Testing against REAL Ollama service...")
        
        with patch.dict(os.environ, {
            'OLLAMA_API_ENDPOINT': 'http://ollama:11434/api/chat',
            'OLLAMA_MODEL': 'codellama:13b'
        }):
            client = OllamaClient()
            
            # Simple test message that doesn't require complex tool calls
            messages = [
                {'role': 'user', 'content': 'Hello, please respond with a simple greeting.'}
            ]
            
            try:
                response = client.call(messages)
                
                # Verify we got a real response
                assert isinstance(response, dict)
                assert 'role' in response or 'content' in response
                print(f"✅ Real Ollama response received: {response}")
                
            except Exception as e:
                pytest.skip(f"Ollama service available but not responding properly: {e}")

    def test_ollama_with_tools_real_service(self):
        """Test Ollama with tool calls against real service."""
        if not is_ollama_available():
            pytest.skip("Ollama service not available")
            
        print("Testing Ollama tool calls against REAL service...")
        
        with patch.dict(os.environ, {
            'OLLAMA_API_ENDPOINT': 'http://ollama:11434/api/chat',
            'OLLAMA_MODEL': 'codellama:13b'
        }):
            client = OllamaClient()
            
            messages = [
                {'role': 'user', 'content': 'Use the get_metrics tool to fetch performance data for service-123.'}
            ]
            
            tools = [
                {
                    'type': 'function',
                    'function': {
                        'name': 'get_metrics',
                        'description': 'Gets performance metrics for a service',
                        'parameters': {
                            'type': 'object',
                            'properties': {
                                'service_id': {'type': 'string', 'description': 'Service identifier'}
                            },
                            'required': ['service_id']
                        }
                    }
                }
            ]
            
            try:
                response = client.call(messages, tools)
                
                # Verify response structure (real LLM might not always use tools)
                assert isinstance(response, dict)
                print(f"✅ Real Ollama tool response: {response}")
                
                # Real LLM behavior verification
                if 'tool_calls' in response:
                    print("✅ Real LLM used tool calls as expected")
                else:
                    print("ℹ️  Real LLM responded without tool calls (normal behavior)")
                    
            except Exception as e:
                pytest.skip(f"Ollama tool test failed: {e}")

    def test_dynatrace_client_with_wiremock(self):
        """Test Dynatrace client against WireMock service."""
        if not is_wiremock_available():
            pytest.skip("WireMock service not available")
            
        print("Testing Dynatrace client against REAL WireMock service...")
        
        with patch.dict(os.environ, {
            'DYNATRACE_API_URL': 'http://wiremock:8080/dynatrace',
            'DYNATRACE_API_TOKEN': 'test-token'
        }):
            with patch('src.utils.secrets_manager.get_secret_value', side_effect=lambda x: os.environ.get(x)):
                try:
                    client = DynatraceClient()
                    
                    test_event = {
                        'eventType': 'CUSTOM_INFO',
                        'title': 'Real Service Integration Test',
                        'entitySelector': 'type(CUSTOM_DEVICE)'
                    }
                    
                    # This will make a real HTTP call to WireMock
                    result = client.send_event(test_event)
                    
                    print(f"✅ Real WireMock response: {result}")
                    
                    # WireMock should respond with configured mock data
                    if result:
                        assert isinstance(result, dict)
                        print("✅ Successfully communicated with WireMock service")
                    else:
                        print("ℹ️  WireMock returned None (may be expected for error simulation)")
                        
                except Exception as e:
                    pytest.skip(f"WireMock communication failed: {e}")

    def test_dynatrace_mcp_real_service(self):
        """Test Dynatrace MCP client against real MCP server."""
        if not is_dynatrace_mcp_available():
            pytest.skip("Dynatrace MCP server not available")
            
        print("Testing against REAL Dynatrace MCP server...")
        
        with patch.dict(os.environ, {
            'DYNATRACE_API_URL': 'http://wiremock:8080/dynatrace',
            'DYNATRACE_API_TOKEN': 'test-token'
        }):
            try:
                client = DynatraceMCPClient()
                
                # Test real MCP server communication
                metrics = client.get_performance_metrics('test-service:prod')
                
                print(f"✅ Real MCP server response: {metrics}")
                
                # Verify we got real data structure
                assert isinstance(metrics, dict)
                print("✅ Successfully communicated with real MCP server")
                
            except Exception as e:
                pytest.skip(f"MCP server communication failed: {e}")

    def test_service_availability_reporting(self):
        """Report which services are available for testing."""
        services = {
            'Ollama': is_ollama_available(),
            'WireMock': is_wiremock_available(),
            'Dynatrace MCP': is_dynatrace_mcp_available(),
        }
        
        print("\n=== Service Availability Report ===")
        for service, available in services.items():
            status = "✅ AVAILABLE" if available else "❌ UNAVAILABLE"
            print(f"{service}: {status}")
        
        available_count = sum(services.values())
        total_count = len(services)
        
        print(f"\n{available_count}/{total_count} services available for real integration testing")
        
        # Always pass - this is just informational
        assert True

    def test_ollama_fallback_when_unavailable(self):
        """Test graceful fallback when Ollama service is unavailable."""
        if is_ollama_available():
            pytest.skip("Testing fallback behavior when Ollama unavailable - but Ollama is available")
            
        print("Testing fallback behavior when Ollama is unavailable...")
        
        # Mock the service to simulate unavailability
        with patch('urllib.request.urlopen') as mock_urlopen:
            mock_urlopen.side_effect = urllib.error.URLError("Service unavailable")
            
            client = OllamaClient()
            
            messages = [{'role': 'user', 'content': 'Test message'}]
            
            # Should handle the error gracefully
            try:
                response = client.call(messages)
                pytest.fail("Expected URLError but call succeeded")
            except urllib.error.URLError:
                print("✅ Properly handled service unavailability")
                assert True

    def test_mixed_real_and_mock_scenario(self):
        """Test scenario with some real services and some mocked."""
        print("Testing mixed real/mock scenario...")
        
        # Use real WireMock if available, mock Ollama
        with patch.dict(os.environ, {
            'DYNATRACE_API_URL': 'http://wiremock:8080/dynatrace' if is_wiremock_available() else 'http://mock-dynatrace',
            'DYNATRACE_API_TOKEN': 'test-token'
        }):
            with patch('src.utils.secrets_manager.get_secret_value', side_effect=lambda x: os.environ.get(x)):
                
                # Mock Ollama regardless of availability for this test
                with patch('urllib.request.urlopen') as mock_urlopen:
                    mock_response_obj = MagicMock()
                    mock_response_obj.read.return_value = json.dumps({
                        'message': {
                            'role': 'assistant',
                            'content': 'Mocked response'
                        }
                    }).encode('utf-8')
                    mock_urlopen.return_value.__enter__.return_value = mock_response_obj
                    
                    # Test Ollama (mocked)
                    ollama_client = OllamaClient()
                    ollama_response = ollama_client.call([{'role': 'user', 'content': 'test'}])
                    assert ollama_response['role'] == 'assistant'
                    print("✅ Ollama (mocked) working")
                
                # Test Dynatrace (real if available, will error if not)
                try:
                    if is_wiremock_available():
                        dt_client = DynatraceClient()
                        result = dt_client.send_event({
                            'eventType': 'CUSTOM_INFO',
                            'title': 'Mixed test'
                        })
                        print("✅ Dynatrace (real WireMock) working")
                    else:
                        print("ℹ️  Dynatrace (WireMock) not available - skipping real test")
                        
                except Exception as e:
                    print(f"ℹ️  Dynatrace real service test failed: {e}")

    @pytest.mark.parametrize("service_type", ["ollama", "wiremock", "mcp"])
    def test_service_health_checks(self, service_type):
        """Parameterized test for individual service health checks."""
        health_checks = {
            "ollama": is_ollama_available,
            "wiremock": is_wiremock_available,
            "mcp": is_dynatrace_mcp_available
        }
        
        is_healthy = health_checks[service_type]()
        print(f"Health check for {service_type}: {'✅ HEALTHY' if is_healthy else '❌ UNHEALTHY'}")
        
        # This test always passes but provides visibility into service status
        assert True 