#!/bin/bash

# Script to run real service integration tests
# Usage: ./run_real_service_tests.sh [mode]
# Modes: auto (default), always, never

set -e

MODE=${1:-auto}

echo "🚀 Starting Real Service Integration Tests"
echo "Mode: $MODE"
echo "=================================="

# Set environment variables
export USE_REAL_SERVICES=$MODE
export OLLAMA_TIMEOUT=30
export WIREMOCK_TIMEOUT=10
export MCP_TIMEOUT=15

# Function to check if services are running
check_services() {
    echo "🔍 Checking service availability..."
    
    # Check if we're running in Docker Compose context
    if docker-compose ps | grep -q "sre-agent"; then
        echo "✅ Running in Docker Compose context"
        
        # Check individual services
        services=("ollama" "wiremock" "dynatrace-mcp-server")
        
        for service in "${services[@]}"; do
            if docker-compose ps | grep -q "$service.*Up"; then
                echo "✅ $service is running"
            else
                echo "❌ $service is not running"
            fi
        done
    else
        echo "ℹ️  Not running in Docker Compose context"
    fi
}

# Function to run tests with specific mode
run_tests() {
    local test_mode=$1
    echo ""
    echo "🧪 Running tests in '$test_mode' mode..."
    
    export USE_REAL_SERVICES=$test_mode
    
    if [ "$test_mode" = "docker" ]; then
        # Run via Docker Compose
        docker-compose run --rm real-service-tests
    else
        # Run locally
        pytest tests/integration/test_real_service_integration.py -v -s --tb=short
    fi
}

# Main execution
case $MODE in
    "auto")
        echo "🔄 Auto mode: Will use real services if available, mocks otherwise"
        check_services
        run_tests "auto"
        ;;
    "always")
        echo "🎯 Always mode: Will attempt to use real services (may fail if unavailable)"
        check_services
        run_tests "always"
        ;;
    "never")
        echo "🎭 Never mode: Will use mocks for all services"
        run_tests "never"
        ;;
    "docker")
        echo "🐳 Docker mode: Running via Docker Compose"
        check_services
        run_tests "docker"
        ;;
    "report")
        echo "📊 Report mode: Show service availability only"
        check_services
        pytest tests/integration/test_real_service_integration.py::TestRealServiceIntegration::test_service_availability_reporting -v -s
        ;;
    *)
        echo "❌ Invalid mode: $MODE"
        echo "Valid modes: auto, always, never, docker, report"
        exit 1
        ;;
esac

echo ""
echo "✅ Real service integration tests completed!" 