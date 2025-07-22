"""
Configuration for integration tests - controls real service vs mock behavior.
"""
import os
from typing import Dict, Any


class TestConfig:
    """Configuration for integration test behavior."""
    
    def __init__(self):
        self.use_real_services = os.environ.get('USE_REAL_SERVICES', 'auto').lower()
        self.service_timeouts = {
            'ollama': int(os.environ.get('OLLAMA_TIMEOUT', '30')),
            'wiremock': int(os.environ.get('WIREMOCK_TIMEOUT', '10')),
            'mcp': int(os.environ.get('MCP_TIMEOUT', '15'))
        }
        
    def should_use_real_service(self, service_name: str) -> bool:
        """Determine if we should use real service or mock for a given service."""
        if self.use_real_services == 'never':
            return False
        elif self.use_real_services == 'always':
            return True
        elif self.use_real_services == 'auto':
            # Auto mode: use real service if available
            return self._check_service_availability(service_name)
        
        return False
    
    def _check_service_availability(self, service_name: str) -> bool:
        """Check if a service is available by making a health check request."""
        import requests
        
        try:
            service_urls = {
                'ollama': 'http://ollama:11434/api/version',
                'wiremock': 'http://wiremock:8080/__admin/health',
                'mcp': 'http://dynatrace-mcp-server:3000/health'
            }
            
            url = service_urls.get(service_name)
            if not url:
                return False
                
            response = requests.get(url, timeout=5)
            return response.status_code < 500
        except (requests.exceptions.RequestException, Exception):
            return False
    
    def get_service_config(self, service_name: str) -> Dict[str, Any]:
        """Get configuration for a specific service."""
        configs = {
            'ollama': {
                'endpoint': os.environ.get('OLLAMA_API_ENDPOINT', 'http://ollama:11434/api/chat'),
                'model': os.environ.get('OLLAMA_MODEL', 'codellama:13b'),
                'timeout': self.service_timeouts['ollama']
            },
            'wiremock': {
                'base_url': 'http://wiremock:8080',
                'dynatrace_url': 'http://wiremock:8080/dynatrace',
                'timeout': self.service_timeouts['wiremock']
            },
            'mcp': {
                'server_url': os.environ.get('DYNATRACE_MCP_SERVER_URL', 'http://dynatrace-mcp-server:3000'),
                'timeout': self.service_timeouts['mcp']
            }
        }
        
        return configs.get(service_name, {})


# Global test configuration instance
test_config = TestConfig()


def get_test_mode_description() -> str:
    """Get a description of the current test mode."""
    mode = test_config.use_real_services
    
    descriptions = {
        'never': 'All services mocked (fastest, most reliable)',
        'always': 'All services real (slowest, most realistic)',
        'auto': 'Real services when available, mocks as fallback (balanced)'
    }
    
    return descriptions.get(mode, f'Unknown mode: {mode}')


def print_test_configuration():
    """Print current test configuration for debugging."""
    print("\n=== Integration Test Configuration ===")
    print(f"Mode: {test_config.use_real_services}")
    print(f"Description: {get_test_mode_description()}")
    print("\nService Configuration:")
    
    services = ['ollama', 'wiremock', 'mcp']
    for service in services:
        will_use_real = test_config.should_use_real_service(service)
        config = test_config.get_service_config(service)
        
        print(f"  {service.upper()}:")
        print(f"    Real Service: {'✅ YES' if will_use_real else '❌ NO (mocked)'}")
        print(f"    Timeout: {config.get('timeout', 'N/A')}s")
        
        if service == 'ollama':
            print(f"    Endpoint: {config.get('endpoint', 'N/A')}")
            print(f"    Model: {config.get('model', 'N/A')}")
        elif service == 'wiremock':
            print(f"    Base URL: {config.get('base_url', 'N/A')}")
        elif service == 'mcp':
            print(f"    Server URL: {config.get('server_url', 'N/A')}")
    
    print("\nEnvironment Variables:")
    env_vars = [
        'USE_REAL_SERVICES', 'OLLAMA_API_ENDPOINT', 'OLLAMA_MODEL',
        'DYNATRACE_MCP_SERVER_URL', 'OLLAMA_TIMEOUT', 'WIREMOCK_TIMEOUT', 'MCP_TIMEOUT'
    ]
    
    for var in env_vars:
        value = os.environ.get(var, 'Not set')
        print(f"  {var}: {value}")
    
    print("=" * 40) 