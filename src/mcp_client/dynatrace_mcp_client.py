"""This module contains a client for the Dynatrace MCP API."""
import os
import json
import requests
from typing import Optional, Dict, Any, Tuple
from .base import MCPClient


class DynatraceMCPClient(MCPClient):
    """A client for the Dynatrace MCP API."""
    def __init__(self, api_url=None, api_token=None):
        self.api_url = api_url or os.environ.get("DYNATRACE_API_URL")
        self.api_token = api_token or os.environ.get("DYNATRACE_API_TOKEN")
        if not all([self.api_url, self.api_token]):
            raise ValueError("Dynatrace API URL or Token not configured.")
        self.headers = {
            "Authorization": f"Api-Token {self.api_token}",
            "Content-Type": "application/json"
        }

    def _json_rpc_request(self, method, params):
        """Simulates a JSON-RPC request to the Dynatrace API."""
        if not hasattr(self, f"_query_{method}"):
            raise NotImplementedError(f"Method '{method}' is not supported.")

        # This is a simplified simulation. A real implementation would have
        # a single endpoint and route based on the 'method' parameter.
        # Here, we map the method to the corresponding internal function.
        query_function = getattr(self, f"_query_{method}")
        return query_function(**params)

    def _query_entities(self, entity_selector):
        """Queries the Dynatrace Entities API to discover services."""
        params = {
            "entitySelector": entity_selector,
            "fields": "displayName,tags,properties"
        }
        entities_endpoint = f"{self.api_url}/api/v2/entities"
        try:
            response = requests.get(
                entities_endpoint, headers=self.headers, params=params, timeout=10
            )
            response.raise_for_status()
            return response.json().get("entities", [])
        except requests.exceptions.RequestException as e:
            print(f"Error querying entities: {e}")
        return []

    def _query_historical_metrics(self, entity_selector, days=7):
        """Queries historical metrics for trend analysis."""
        metric_selectors = [
            "builtin:service.cpu.time",
            "builtin:service.memory.usage",
            "builtin:service.requestCount.rate",
            "builtin:service.response.time"
        ]
        params = {
            "metricSelector": ",".join(metric_selectors),
            "entitySelector": entity_selector,
            "resolution": "1h",
            "from": f"now-{days}d"
        }
        metrics_endpoint = f"{self.api_url}/api/v2/metrics/query"
        try:
            response = requests.get(
                metrics_endpoint, headers=self.headers, params=params, timeout=15
            )
            response.raise_for_status()
            data = response.json()
            
            # Process metrics to calculate averages and trends
            results = {}
            for item in data.get("result", []):
                metric_id = item.get("metricId")
                data_points = item.get("data", [{}])[0].get("values", [])
                if data_points:
                    # Calculate basic statistics
                    values = [point for point in data_points if point is not None]
                    if values:
                        results[metric_id] = {
                            "avg": sum(values) / len(values),
                            "max": max(values),
                            "min": min(values),
                            "data_points": len(values),
                            "days_available": days
                        }
            return results
        except requests.exceptions.RequestException as e:
            print(f"Error querying historical metrics: {e}")
        return {}

    def _query_metrics_batch(self, entity_selector):
        """Queries all required metrics for a given entity in a single API call."""
        metric_selectors = [
            "builtin:container.cpu.usage.millicores:percentile(90)",
            "builtin:container.memory.workingSet.bytes:percentile(90)",
            "builtin:container.cpu.requests",
            "builtin:container.memory.requests"
        ]
        params = {
            "metricSelector": ",".join(metric_selectors),
            "entitySelector": entity_selector,
            "resolution": "1h"
        }
        metrics_endpoint = f"{self.api_url}/api/v2/metrics/query"
        try:
            response = requests.get(
                metrics_endpoint, headers=self.headers, params=params, timeout=10
            )
            response.raise_for_status()
            data = response.json()
            results = {
                item.get("metricId"): item.get("data", [{}])[0].get("values", [None])[0]
                for item in data.get("result", [])
            }
            return results
        except (requests.exceptions.RequestException, IndexError, TypeError) as e:
            print(f"Error or empty response querying metrics batch: {e}")
        return {}

    def _query_problems(self, entity_selector):
        """Queries the Dynatrace Problems API."""
        params = {"entitySelector": entity_selector, "status": "OPEN"}
        problems_endpoint = f"{self.api_url}/api/v2/problems"
        try:
            response = requests.get(
                problems_endpoint, headers=self.headers, params=params, timeout=10
            )
            response.raise_for_status()
            return [
                {"title": p.get("title"), "severity": p.get("severityLevel")}
                for p in response.json().get("problems", [])
            ]
        except requests.exceptions.RequestException as e:
            print(f"Error querying problems: {e}")
        return []

    def _query_oom_kills(self, entity_selector):
        """Queries the Dynatrace Events API for OOMKills."""
        params = {
            "eventSelector": "eventType(KUBERNETES_EVENT),kubernetes.event.reason(OOMKill)",
            "entitySelector": entity_selector,
            "from": "now-7d"
        }
        events_endpoint = f"{self.api_url}/api/v2/events"
        try:
            response = requests.get(
                events_endpoint, headers=self.headers, params=params, timeout=10
            )
            response.raise_for_status()
            return response.json().get("totalCount", 0)
        except requests.exceptions.RequestException as e:
            print(f"Error querying events: {e}")
        return 0

    def _query_slos(self, entity_selector):
        """Queries the Dynatrace SLO API."""
        params = {"entitySelector": entity_selector, "timeFrame": "now-1h"}
        slo_endpoint = f"{self.api_url}/api/v2/slo"
        try:
            response = requests.get(
                slo_endpoint, headers=self.headers, params=params, timeout=10
            )
            response.raise_for_status()
            slos = response.json().get("slos", [])
            # Return a concise summary of each SLO
            return [
                {
                    "name": s.get("name"),
                    "status": s.get("status"),
                    "value": s.get("evaluatedPercentage"),
                    "errorBudgetRemaining": s.get("errorBudgetRemainingPercentage")
                } for s in slos
            ]
        except requests.exceptions.RequestException as e:
            print(f"Error querying SLOs (this may be expected if none are defined): {e}")
        return []

    def check_data_availability(self, app_name: str, namespace: str) -> Tuple[str, Optional[Dict[str, Any]]]:
        """Check what historical data is available for an application."""
        print(f"Checking data availability for {app_name} in namespace {namespace}...")
        
        try:
            # First, try to discover the entity
            entity_id = self.discover_entity(app_name, namespace)
            if not entity_id:
                return 'no_historical_data', None
            
            # Check for historical metrics
            entity_selector = f'type(SERVICE),entityId({entity_id})'
            historical_data = self._json_rpc_request("historical_metrics", {
                "entity_selector": entity_selector, 
                "days": 7
            })
            
            if not historical_data:
                return 'no_historical_data', None
            
            # Analyze data completeness
            total_metrics = 0
            available_metrics = 0
            min_data_points = float('inf')
            
            for metric_name, metric_data in historical_data.items():
                total_metrics += 1
                if metric_data and metric_data.get('data_points', 0) > 0:
                    available_metrics += 1
                    min_data_points = min(min_data_points, metric_data.get('data_points', 0))
            
            if available_metrics == 0:
                return 'no_historical_data', None
            
            completeness = (available_metrics / total_metrics) * 100 if total_metrics > 0 else 0
            days_available = min(7, max(1, min_data_points / 24)) if min_data_points != float('inf') else 0
            
            if days_available >= 5 and completeness >= 80:
                return 'full_historical_data', {
                    'days_available': int(days_available),
                    'completeness': completeness,
                    'entity_id': entity_id
                }
            elif days_available >= 1 and completeness >= 30:
                return 'partial_data', {
                    'days_available': int(days_available),
                    'completeness': completeness,
                    'entity_id': entity_id
                }
            else:
                return 'no_historical_data', None
                
        except Exception as e:
            print(f"Error checking data availability: {e}")
            return 'no_historical_data', None

    def discover_entity(self, app_name: str, namespace: str) -> Optional[str]:
        """Discover the Dynatrace entity ID for an application."""
        print(f"Discovering entity for {app_name} in namespace {namespace}...")
        
        try:
            # Try multiple entity selector patterns
            selectors = [
                f'type(SERVICE),entityName("{app_name}")',
                f'type(SERVICE),tag("app:{app_name}")',
                f'type(SERVICE),tag("k8s.namespace.name:{namespace}"),entityName.contains("{app_name}")',
                f'type(SERVICE),tag("k8s.deployment.name:{app_name}")'
            ]
            
            for selector in selectors:
                entities = self._json_rpc_request("entities", {"entity_selector": selector})
                if entities:
                    # Return the first matching entity
                    return entities[0].get("entityId")
            
            return None
            
        except Exception as e:
            print(f"Error discovering entity: {e}")
            return None

    def get_historical_metrics(self, entity_id: str, days: int = 7) -> Dict[str, Any]:
        """Get historical metrics for trend analysis."""
        print(f"Fetching historical metrics for {entity_id} over {days} days...")
        
        entity_selector = f'type(SERVICE),entityId({entity_id})'
        return self._json_rpc_request("historical_metrics", {
            "entity_selector": entity_selector,
            "days": days
        })

    def get_trend_analysis(self, entity_id: str, days: int = 7) -> Dict[str, Any]:
        """Analyze metrics trends to infer traffic patterns."""
        print(f"Analyzing trends for {entity_id} over {days} days...")
        
        historical_data = self.get_historical_metrics(entity_id, days)
        
        # Analyze trends
        analysis = {
            "traffic_pattern": "steady",  # Default
            "cpu_trend": "stable",
            "memory_trend": "stable",
            "request_rate_trend": "stable"
        }
        
        try:
            # Analyze CPU trends
            cpu_data = historical_data.get("builtin:service.cpu.time", {})
            if cpu_data and cpu_data.get('data_points', 0) > 0:
                avg_cpu = cpu_data.get('avg', 0)
                max_cpu = cpu_data.get('max', 0)
                
                if max_cpu > avg_cpu * 1.5:
                    analysis["traffic_pattern"] = "peak_hours"
                    analysis["cpu_trend"] = "spiky"
                elif max_cpu > avg_cpu * 1.2:
                    analysis["traffic_pattern"] = "gradual_growth"
                    analysis["cpu_trend"] = "increasing"
            
            # Analyze request rate trends
            request_data = historical_data.get("builtin:service.requestCount.rate", {})
            if request_data and request_data.get('data_points', 0) > 0:
                avg_requests = request_data.get('avg', 0)
                max_requests = request_data.get('max', 0)
                
                if max_requests > avg_requests * 2:
                    analysis["traffic_pattern"] = "high_peak_hours"
                    analysis["request_rate_trend"] = "increasing"
                elif max_requests > avg_requests * 1.3:
                    analysis["request_rate_trend"] = "moderate_growth"
            
        except Exception as e:
            print(f"Error in trend analysis: {e}")
        
        return analysis

    def get_performance_metrics(self, entity_id):
        """Gets key performance metrics for a service."""
        print(f"Fetching performance metrics for {entity_id} from Dynatrace...")
        entity_selector = f'type(PROCESS_GROUP_INSTANCE),tag({entity_id})'
        
        metrics = self._json_rpc_request("metrics_batch", {"entity_selector": entity_selector})
        
        mem_usage_bytes = metrics.get(
            "builtin:container.memory.workingSet.bytes:percentile(90)"
        )
        mem_requests_bytes = metrics.get("builtin:container.memory.requests")
        
        performance_data = {
            "cpu_usage_millicores_p90": metrics.get(
                "builtin:container.cpu.usage.millicores:percentile(90)"
            ),
            "memory_usage_mb_p90": mem_usage_bytes / (1024*1024)
            if mem_usage_bytes else None,
            "pod_cpu_requests_millicores": metrics.get(
                "builtin:container.cpu.requests"
            ),
            "pod_memory_requests_mb": mem_requests_bytes / (1024*1024)
            if mem_requests_bytes else None
        }
        
        print(f"Performance metrics: {json.dumps(performance_data, indent=2)}")
        return performance_data
    
    def get_health_events(self, entity_id):
        """Gets health events (e.g., problems, OOM kills) for a service."""
        print(f"Fetching health events for {entity_id} from Dynatrace...")
        entity_selector = f'type(PROCESS_GROUP_INSTANCE),tag({entity_id})'
        
        active_problems = self._json_rpc_request("problems", {"entity_selector": entity_selector})
        oom_kill_count = self._json_rpc_request("oom_kills", {"entity_selector": entity_selector})
        
        health_data = {
            "active_problem_count": len(active_problems),
            "active_problems": active_problems,
            "recent_oom_kills": oom_kill_count
        }
        
        print(f"Health events: {json.dumps(health_data, indent=2)}")
        return health_data
    
    def get_service_level_objectives(self, entity_id):
        """Gets the status of all SLOs related to a service."""
        print(f"Fetching SLOs for {entity_id} from Dynatrace...")
        entity_selector = f'type(PROCESS_GROUP_INSTANCE),tag({entity_id})'
        
        slos = self._json_rpc_request("slos", {"entity_selector": entity_selector})
        
        print(f"SLOs: {json.dumps(slos, indent=2)}")
        return slos

    def get_scaling_context(self, entity_id):
        """Builds a comprehensive performance and health context for a service from Dynatrace."""
        print(f"Fetching real performance context for {entity_id} from Dynatrace...")
        entity_selector = f'type(PROCESS_GROUP_INSTANCE),tag({entity_id})'

        metrics = self._json_rpc_request("metrics_batch", {"entity_selector": entity_selector})
        active_problems = self._json_rpc_request("problems", {"entity_selector": entity_selector})
        oom_kill_count = self._json_rpc_request("oom_kills", {"entity_selector": entity_selector})
        slos = self._json_rpc_request("slos", {"entity_selector": entity_selector})

        mem_usage_bytes = metrics.get(
            "builtin:container.memory.workingSet.bytes:percentile(90)"
        )
        mem_requests_bytes = metrics.get("builtin:container.memory.requests")

        context = {
            "performance_metrics": {
                "cpu_usage_millicores_p90": metrics.get(
                    "builtin:container.cpu.usage.millicores:percentile(90)"
                ),
                "memory_usage_mb_p90": mem_usage_bytes / (1024*1024)
                if mem_usage_bytes else None,
                "pod_cpu_requests_millicores": metrics.get(
                    "builtin:container.cpu.requests"
                ),
                "pod_memory_requests_mb": mem_requests_bytes / (1024*1024)
                if mem_requests_bytes else None
            },
            "health_events": {
                "active_problem_count": len(active_problems),
                "active_problems": active_problems,
                "recent_oom_kills": oom_kill_count
            },
            "service_level_objectives": slos
        }

        print(f"Assembled context for LLM: {json.dumps(context, indent=2)}")
        return context
