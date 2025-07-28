"""
Performance tests for SRE Orchestration Agent using Locust.

This file contains performance tests for the main API endpoints:
- Scaling suggestion endpoint
- Quality gate endpoint
- Health check endpoint
"""

import json
import random
from locust import HttpUser, task, between, events
from typing import Dict, Any


class SREAgentUser(HttpUser):
    """Simulates a user interacting with the SRE Agent API."""
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between requests
    
    def on_start(self):
        """Initialize test data when the user starts."""
        self.test_apps = [
            {
                "name": "user-service",
                "namespace": "user-service-prod",
                "version": "1.2.3",
                "team": "platform"
            },
            {
                "name": "payment-service", 
                "namespace": "payment-service-prod",
                "version": "2.1.0",
                "team": "finance"
            },
            {
                "name": "notification-service",
                "namespace": "notification-service-prod", 
                "version": "1.0.5",
                "team": "platform"
            },
            {
                "name": "auth-service",
                "namespace": "auth-service-prod",
                "version": "3.0.1", 
                "team": "security"
            },
            {
                "name": "analytics-service",
                "namespace": "analytics-service-prod",
                "version": "1.1.2",
                "team": "data"
            }
        ]
        
        self.deployment_contexts = [
            {
                "environment": "prod",
                "deployment_name": "rolling-update",
                "architecture": "amd64",
                "cluster_name": "eks-prod"
            },
            {
                "environment": "prod", 
                "deployment_name": "blue-green",
                "architecture": "amd64",
                "cluster_name": "eks-prod"
            },
            {
                "environment": "prod",
                "deployment_name": "canary",
                "architecture": "amd64", 
                "cluster_name": "eks-prod"
            }
        ]

    @task(3)
    def test_scaling_suggestion(self):
        """Test scaling suggestion endpoint with realistic data."""
        app = random.choice(self.test_apps)
        context = random.choice(self.deployment_contexts)
        
        payload = {
            "suggestion_type": "kubernetes_scaling",
            "application": app,
            "deployment_context": context
        }
        
        headers = {
            "Content-Type": "application/json",
            "X-Request-ID": f"perf-test-{random.randint(1000, 9999)}"
        }
        
        with self.client.post(
            "/suggestion",
            json=payload,
            headers=headers,
            catch_response=True,
            name="scaling_suggestion"
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "suggestion" in data and "suggestion_source" in data:
                        response.success()
                    else:
                        response.failure("Invalid response structure")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"HTTP {response.status_code}")

    @task(2)
    def test_quality_gate(self):
        """Test quality gate endpoint with realistic data."""
        app = random.choice(self.test_apps)
        
        payload = {
            "application": {
                **app,
                "commit_sha": f"abc123def456{random.randint(100, 999)}",
                "artifact_id": f"artifact-{app['name']}-{app['version']}-{random.randint(1000, 9999)}"
            }
        }
        
        headers = {
            "Content-Type": "application/json",
            "X-Request-ID": f"perf-test-{random.randint(1000, 9999)}"
        }
        
        with self.client.post(
            "/gate",
            json=payload,
            headers=headers,
            catch_response=True,
            name="quality_gate"
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "status" in data and "score" in data:
                        response.success()
                    else:
                        response.failure("Invalid response structure")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"HTTP {response.status_code}")

    @task(1)
    def test_health_check(self):
        """Test health check endpoint."""
        with self.client.get(
            "/health",
            catch_response=True,
            name="health_check"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")

    @task(1)
    def test_root_endpoint(self):
        """Test root endpoint."""
        with self.client.get(
            "/",
            catch_response=True,
            name="root_endpoint"
        ) as response:
            if response.status_code in [200, 404]:  # 404 is acceptable for root
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")


class SREAgentLoadTest(HttpUser):
    """Simulates high-load scenarios for stress testing."""
    
    wait_time = between(0.1, 0.5)  # Faster requests for load testing
    
    def on_start(self):
        """Initialize test data."""
        self.test_apps = [
            {"name": f"load-test-app-{i}", "namespace": f"load-test-{i}-prod"} 
            for i in range(1, 11)
        ]

    @task(5)
    def rapid_scaling_requests(self):
        """Rapid scaling suggestion requests for load testing."""
        app = random.choice(self.test_apps)
        
        payload = {
            "suggestion_type": "kubernetes_scaling",
            "application": {
                **app,
                "version": "1.0.0",
                "team": "load-test"
            },
            "deployment_context": {
                "environment": "prod",
                "deployment_name": "load-test",
                "architecture": "amd64",
                "cluster_name": "eks-prod"
            }
        }
        
        with self.client.post(
            "/suggestion",
            json=payload,
            catch_response=True,
            name="rapid_scaling_requests"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")

    @task(3)
    def rapid_quality_gates(self):
        """Rapid quality gate requests for load testing."""
        app = random.choice(self.test_apps)
        
        payload = {
            "application": {
                **app,
                "version": "1.0.0",
                "team": "load-test",
                "commit_sha": f"load{random.randint(100000, 999999)}",
                "artifact_id": f"load-artifact-{random.randint(1000, 9999)}"
            }
        }
        
        with self.client.post(
            "/gate",
            json=payload,
            catch_response=True,
            name="rapid_quality_gates"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")


# Custom event handlers for detailed monitoring
@events.request.add_listener
def my_request_handler(request_type, name, response_time, response_length, response, context, exception, start_time, url, **kwargs):
    """Custom request handler for detailed monitoring."""
    if exception:
        print(f"Request failed: {name} - {exception}")
    elif response and response.status_code >= 400:
        print(f"Request error: {name} - HTTP {response.status_code}")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when the test starts."""
    print("🚀 Starting SRE Agent Performance Tests")
    print(f"Target host: {environment.host}")
    print(f"Number of users: {environment.runner.user_count if environment.runner else 'Unknown'}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when the test stops."""
    print("✅ SRE Agent Performance Tests Completed")
    if environment.stats:
        print(f"Total requests: {environment.stats.total.num_requests}")
        print(f"Failed requests: {environment.stats.total.num_failures}")
        print(f"Average response time: {environment.stats.total.avg_response_time:.2f}ms") 