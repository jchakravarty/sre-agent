# Real Service Integration Testing

## Overview

This document describes the **Real Service Integration Testing** approach implemented for the SRE Agent. This testing strategy provides **conditional integration tests** that connect to actual services when available, while gracefully falling back to mocks when services are unavailable.

## Why Real Service Integration Testing?

### Benefits
1. **Realistic Validation**: Tests against actual service behavior, not just mocked responses
2. **API Contract Verification**: Ensures our code works with real API responses and formats
3. **Network & Timing Validation**: Tests real network conditions and response times
4. **Service Compatibility**: Validates compatibility with actual service versions
5. **End-to-End Confidence**: Provides higher confidence in production behavior

### Challenges Addressed
- **Reliability**: Services may be unavailable during testing
- **Speed**: Real services are slower than mocks
- **Consistency**: Real services may have varying responses
- **Environment**: Not all environments have access to all services

## Test Modes

### Auto Mode (Default)
```bash
USE_REAL_SERVICES=auto
```
- **Behavior**: Uses real services when available, mocks when unavailable
- **Best for**: CI/CD pipelines, development environments
- **Advantages**: Balanced approach, maximum coverage with reliability

### Always Mode
```bash
USE_REAL_SERVICES=always
```
- **Behavior**: Always attempts to use real services
- **Best for**: Integration environment testing, manual verification
- **Advantages**: Maximum realism
- **Disadvantages**: Tests fail if services unavailable

### Never Mode
```bash
USE_REAL_SERVICES=never
```
- **Behavior**: Always uses mocks
- **Best for**: Unit testing, fast feedback loops
- **Advantages**: Fast, reliable, no external dependencies
- **Disadvantages**: Less realistic

## Services Tested

### Ollama LLM Service
- **Real Service**: `http://ollama:11434`
- **Health Check**: `/api/version`
- **Tests**: Basic chat, tool calling, error handling
- **Timeout**: 30 seconds (configurable)

### WireMock (Dynatrace Simulation)
- **Real Service**: `http://wiremock:8080`
- **Health Check**: `/__admin/health`
- **Tests**: API calls, event sending, metric retrieval
- **Timeout**: 10 seconds (configurable)

### Dynatrace MCP Server
- **Real Service**: `http://dynatrace-mcp-server:3000`
- **Health Check**: `/health`
- **Tests**: MCP protocol, metric processing, tool invocation
- **Timeout**: 15 seconds (configurable)

## Running Tests

### Using the Script
```bash
# Auto mode (default)
./run_real_service_tests.sh

# Specific modes
./run_real_service_tests.sh always
./run_real_service_tests.sh never
./run_real_service_tests.sh docker

# Service availability report
./run_real_service_tests.sh report
```

### Using Docker Compose
```bash
# Run all services and tests
docker-compose up -d
docker-compose run --rm real-service-tests

# Run specific service
docker-compose run --rm real-service-tests pytest tests/integration/test_real_service_integration.py::TestRealServiceIntegration::test_ollama_real_service_integration -v
```

### Using pytest Directly
```bash
# All real service tests
pytest tests/integration/test_real_service_integration.py -v

# Specific test
pytest tests/integration/test_real_service_integration.py::TestRealServiceIntegration::test_service_availability_reporting -v
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `USE_REAL_SERVICES` | `auto` | Test mode: `auto`, `always`, `never` |
| `OLLAMA_TIMEOUT` | `30` | Timeout for Ollama service calls (seconds) |
| `WIREMOCK_TIMEOUT` | `10` | Timeout for WireMock service calls (seconds) |
| `MCP_TIMEOUT` | `15` | Timeout for MCP server calls (seconds) |
| `OLLAMA_API_ENDPOINT` | `http://ollama:11434/api/chat` | Ollama service endpoint |
| `OLLAMA_MODEL` | `codellama:13b` | Ollama model to use |
| `DYNATRACE_MCP_SERVER_URL` | `http://dynatrace-mcp-server:3000` | MCP server URL |

### Service Configuration
```python
from tests.integration.test_config import test_config, print_test_configuration

# Print current configuration
print_test_configuration()

# Check if service should use real implementation
if test_config.should_use_real_service('ollama'):
    # Use real Ollama service
    pass
else:
    # Use mocked service
    pass
```

## Test Structure

### Test Categories

1. **Service Availability Tests**
   - Health checks for all services
   - Parameterized tests for individual services
   - Service availability reporting

2. **Real Service Integration Tests**
   - Skip if service unavailable
   - Test actual API calls and responses
   - Verify real data structures

3. **Fallback Behavior Tests**
   - Test graceful degradation when services unavailable
   - Verify error handling

4. **Mixed Scenario Tests**
   - Some services real, some mocked
   - Test realistic deployment scenarios

### Example Test Structure
```python
@pytest.mark.skipif(not is_ollama_available(), reason="Ollama service not available")
def test_ollama_real_service_integration(self):
    """Test integration with real Ollama service."""
    print("Testing against REAL Ollama service...")
    
    # Test implementation
    client = OllamaClient()
    response = client.call(messages)
    
    # Verify real response structure
    assert isinstance(response, dict)
    print(f"✅ Real Ollama response received: {response}")
```

## Best Practices

### Test Design
1. **Graceful Degradation**: Tests should skip gracefully when services unavailable
2. **Clear Logging**: Print whether using real or mocked services
3. **Timeout Handling**: Use appropriate timeouts for each service
4. **Error Handling**: Test both success and failure scenarios

### CI/CD Integration
1. **Auto Mode**: Use auto mode in CI/CD for balanced testing
2. **Service Health**: Include service health checks in pipeline
3. **Conditional Steps**: Skip certain tests based on service availability
4. **Reporting**: Generate reports showing which services were tested

### Development Workflow
1. **Local Development**: Use auto mode for development
2. **Integration Testing**: Use always mode for thorough integration testing
3. **Unit Testing**: Use never mode for fast unit test feedback
4. **Debugging**: Use report mode to check service availability

## Monitoring and Reporting

### Service Health Reporting
```bash
# Check service availability
./run_real_service_tests.sh report
```

### Test Results
- **JUnit XML**: Generated at `/app/test-reports/real-service-junit.xml`
- **Console Output**: Detailed logging of service usage
- **Service Status**: Clear indication of real vs mocked services

### Example Output
```
=== Service Availability Report ===
Ollama: ✅ AVAILABLE
WireMock: ✅ AVAILABLE
Dynatrace MCP: ❌ UNAVAILABLE

2/3 services available for real integration testing

=== Integration Test Configuration ===
Mode: auto
Description: Real services when available, mocks as fallback (balanced)

Service Configuration:
  OLLAMA:
    Real Service: ✅ YES
    Timeout: 30s
    Endpoint: http://ollama:11434/api/chat
    Model: codellama:13b
  WIREMOCK:
    Real Service: ✅ YES
    Timeout: 10s
    Base URL: http://wiremock:8080
  MCP:
    Real Service: ❌ NO (mocked)
    Timeout: 15s
    Server URL: http://dynatrace-mcp-server:3000
```

## Troubleshooting

### Common Issues

1. **Service Not Available**
   - Check Docker Compose services are running
   - Verify network connectivity
   - Check service health endpoints

2. **Timeout Errors**
   - Increase timeout values
   - Check service performance
   - Verify network latency

3. **Authentication Errors**
   - Verify API tokens and credentials
   - Check environment variable configuration
   - Ensure WireMock stubs are configured

### Debugging Commands
```bash
# Check service status
docker-compose ps

# Check service logs
docker-compose logs ollama
docker-compose logs wiremock
docker-compose logs dynatrace-mcp-server

# Test service health manually
curl http://localhost:11434/api/version  # Ollama
curl http://localhost:8080/__admin/health  # WireMock
curl http://localhost:3000/health  # MCP Server
```

## Future Enhancements

1. **Additional Services**: Add more services (GitHub, SonarQube, etc.)
2. **Performance Testing**: Add performance benchmarks for real services
3. **Contract Testing**: Implement contract testing with Pact
4. **Chaos Testing**: Add failure injection for resilience testing
5. **Metrics Collection**: Collect performance metrics during real service testing 