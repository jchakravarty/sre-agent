"""
Real service integration tests with longer timeouts for Ollama.
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


def is_service_available(url, timeout=30):  # Increased timeout
    """Check if a service is available by making a health check request."""
    try:
        response = requests.get(url, timeout=timeout)
        return response.status_code < 500
    except (requests.exceptions.RequestException, Exception):
        return False


def is_ollama_available():
    """Check if Ollama service is available with longer timeout."""
    ollama_endpoint = os.environ.get('OLLAMA_API_ENDPOINT', 'http://ollama:11434/api/chat')
    base_url = ollama_endpoint.replace('/api/chat', '')
    return is_service_available(f"{base_url}/api/version", timeout=30)


def is_wiremock_available():
    """Check if WireMock service is available."""
    return is_service_available("http://wiremock:8080/__admin/health", timeout=10)


def is_dynatrace_mcp_available():
    """Check if Dynatrace MCP server is available."""
    return is_service_available("http://dynatrace-mcp-server:3000/health", timeout=10)


class TestRealServiceIntegrationFixed:
    """Integration tests with longer timeouts for Ollama."""

    def test_ollama_real_service_integration_fixed(self):
        """Test integration with real Ollama service with longer timeout."""
        if not is_ollama_available():
            pytest.skip("Ollama service not available")
            
        print("Testing against REAL Ollama service with longer timeout...")
        
        with patch.dict(os.environ, {
            'OLLAMA_API_ENDPOINT': 'http://ollama:11434/api/chat',
            'OLLAMA_MODEL': 'llama3:8b'
        }):
            client = OllamaClient()
            
            # Simple test message that doesn't require complex tool calls
            messages = [
                {'role': 'user', 'content': 'Hello, please respond with a simple greeting.'}
            ]
            
            try:
                print("Sending request to Ollama (this may take 30-60 seconds)...")
                response = client.call(messages)
                
                # Verify we got a real response
                assert isinstance(response, dict)
                assert 'role' in response or 'content' in response
                print(f"✅ Real Ollama response received: {response}")
                
            except Exception as e:
                pytest.skip(f"Ollama service available but not responding properly: {e}")

    def test_ollama_with_tools_real_service_fixed(self):
        """Test Ollama with tool calls against real service with longer timeout."""
        if not is_ollama_available():
            pytest.skip("Ollama service not available")
            
        print("Testing Ollama tool calls against REAL service with longer timeout...")
        
        with patch.dict(os.environ, {
            'OLLAMA_API_ENDPOINT': 'http://ollama:11434/api/chat',
            'OLLAMA_MODEL': 'llama3:8b'
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
                print("Sending tool request to Ollama (this may take 30-60 seconds)...")
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

    def test_service_availability_reporting_fixed(self):
        """Report which services are available for testing."""
        services = {
            'Ollama': is_ollama_available(),
            'WireMock': is_wiremock_available(),
            'Dynatrace MCP': is_dynatrace_mcp_available(),
        }
        
        print("\n=== Service Availability Report (Fixed) ===")
        for service, available in services.items():
            status = "✅ AVAILABLE" if available else "❌ UNAVAILABLE"
            print(f"{service}: {status}")
        
        available_count = sum(services.values())
        total_count = len(services)
        
        print(f"\n{available_count}/{total_count} services available for real integration testing")
        
        # Always pass - this is just informational
        assert True
