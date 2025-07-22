"""This module contains a mock MCP client for testing purposes."""
from typing import Optional, Dict, Any, Tuple
from .base import MCPClient


class MockMCPClient(MCPClient):
    """A mock MCP client for testing purposes."""
    
    def check_data_availability(self, app_name: str, namespace: str) -> Tuple[str, Optional[Dict[str, Any]]]:
        """Returns mock data availability for testing."""
        print(f"Mock: Checking data availability for {app_name} in namespace {namespace}.")
        
        # Simulate different scenarios based on app name
        if 'new' in app_name.lower():
            return 'no_historical_data', None
        elif 'partial' in app_name.lower():
            return 'partial_data', {'days_available': 3, 'completeness': 65, 'entity_id': f'mock-{app_name}'}
        else:
            return 'full_historical_data', {'days_available': 7, 'completeness': 95, 'entity_id': f'mock-{app_name}'}
    
    def discover_entity(self, app_name: str, namespace: str) -> Optional[str]:
        """Returns mock entity ID for testing."""
        print(f"Mock: Discovering entity for {app_name} in namespace {namespace}.")
        
        # Return None for apps containing 'notfound'
        if 'notfound' in app_name.lower():
            return None
        
        return f"mock-entity-{app_name}-{namespace}"
    
    def get_historical_metrics(self, entity_id: str, days: int = 7) -> Dict[str, Any]:
        """Returns mock historical metrics for testing."""
        print(f"Mock: Fetching historical metrics for {entity_id} over {days} days.")
        
        return {
            "builtin:service.cpu.time": {
                "avg": 45.5,
                "max": 78.2,
                "min": 12.1,
                "data_points": days * 24,
                "days_available": days
            },
            "builtin:service.memory.usage": {
                "avg": 67.3,
                "max": 89.1,
                "min": 45.2,
                "data_points": days * 24,
                "days_available": days
            },
            "builtin:service.requestCount.rate": {
                "avg": 125.7,
                "max": 245.3,
                "min": 45.1,
                "data_points": days * 24,
                "days_available": days
            },
            "builtin:service.response.time": {
                "avg": 82.4,
                "max": 156.8,
                "min": 45.2,
                "data_points": days * 24,
                "days_available": days
            }
        }
    
    def get_trend_analysis(self, entity_id: str, days: int = 7) -> Dict[str, Any]:
        """Returns mock trend analysis for testing."""
        print(f"Mock: Analyzing trends for {entity_id} over {days} days.")
        
        # Simulate different patterns based on entity_id
        if 'peak' in entity_id.lower():
            return {
                "traffic_pattern": "peak_hours",
                "cpu_trend": "spiky",
                "memory_trend": "stable",
                "request_rate_trend": "increasing"
            }
        elif 'growth' in entity_id.lower():
            return {
                "traffic_pattern": "gradual_growth",
                "cpu_trend": "increasing",
                "memory_trend": "increasing",
                "request_rate_trend": "moderate_growth"
            }
        else:
            return {
                "traffic_pattern": "steady",
                "cpu_trend": "stable",
                "memory_trend": "stable",
                "request_rate_trend": "stable"
            }

    def get_scaling_context(self, entity_id):
        """
        Returns a mock context for testing purposes.
        """
        print(f"Returning mock performance context for {entity_id}.")
        return {
            "p95_cpu_usage_millicores": 550,
            "p95_memory_usage_mb": 1200,
            "recent_oom_kills": 0,
            "active_problem_count": 1,
            "active_problem_details": "High CPU saturation on node XYZ",
            "deployment_strategy": "blue-green",
            "current_replicas": 3,
            "service_dependencies": ["redis-cart", "postgres-users"],
            "service_dependents": ["api-gateway"]
        }

    def get_performance_metrics(self, entity_id):
        """
        Returns mock performance metrics for testing purposes.
        """
        print(f"Returning mock performance metrics for {entity_id}.")
        return {
            "cpu_usage_millicores_p90": 800,
            "memory_usage_mb_p90": 1024,
            "pod_cpu_requests_millicores": 500,
            "pod_memory_requests_mb": 512
        }

    def get_health_events(self, entity_id):
        """
        Returns mock health events for testing purposes.
        """
        print(f"Returning mock health events for {entity_id}.")
        return {
            "active_problem_count": 1,
            "recent_oom_kills": 2,
            "active_problems": [
                {"title": "High CPU usage", "severityLevel": "WARNING"}
            ]
        }

    def get_service_level_objectives(self, entity_id):
        """
        Returns mock SLOs for testing purposes.
        """
        print(f"Returning mock SLOs for {entity_id}.")
        return [
            {
                "name": "Response Time SLO",
                "status": "SUCCESS",
                "evaluatedPercentage": 99.5,
                "errorBudgetRemainingPercentage": 85.2
            }
        ]