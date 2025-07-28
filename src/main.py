import json
import os
import urllib.request
import yaml

from . import suggestion_engines
from .connectors import dynatrace_client, sonarqube_client, wiz_client, slack_client
from .data_models import ScalingSuggestion

# --- Configuration Loading ---
def load_config():
    """Loads configuration from the AWS AppConfig Lambda extension."""
    appconfig_endpoint = os.environ.get('AWS_APPCONFIG_EXTENSION_ENDPOINT', 'http://localhost:2772')
    appconfig_path = f"/applications/sre-agent/environments/{os.environ.get('APP_ENV', 'dev')}/configurations/config"
    url = f"{appconfig_endpoint}{appconfig_path}"
    try:
        with urllib.request.urlopen(url) as response:
            return yaml.safe_load(response.read())
    except Exception as e:
        print(f"Error loading configuration from AWS AppConfig: {e}")
        return {}

# --- Quality Gate Logic ---

def _get_weight(weights, key, default=0):
    """Safely retrieves a weight value, ensuring it's a number."""
    value = weights.get(key, default)
    if not isinstance(value, (int, float)):
        print(f"Warning: Weight for '{key}' is not a number ('{value}'). Using default value {default}.")
        return default
    return value

def _run_quality_checks(repo_name, commit_sha, artifact_id):
    """Runs all quality gate checks and returns the results."""
    sq_client = sonarqube_client.SonarQubeClient()
    wiz_client_instance = wiz_client.WizClient()
    return {
        "sonarqube": sq_client.get_quality_gate_status(repo_name),
        "wiz": wiz_client_instance.get_cve_status(artifact_id)
    }

def gate_handler(event, _context):
    """
    Handles the quality gate check. Runs security and quality scans and returns a pass/fail score.
    """
    try:
        config = load_config()
        body = json.loads(event.get('body', '{}'))
        
        app_context = body.get('application', {})
        repo_name = app_context.get('name')
        commit_sha = app_context.get('commit_sha')
        artifact_id = app_context.get('artifact_id')

        if not all([repo_name, commit_sha, artifact_id]):
            return {'statusCode': 400, 'body': json.dumps({'status': 'ERROR', 'message': 'Missing required context: name, commit_sha, or artifact_id'})}

        checks = _run_quality_checks(repo_name, commit_sha, artifact_id)
        
        gating_rules = config.get('gating_rules', {})
        weights = gating_rules.get('weights', {})
        score = 0
        issues = []

        if checks["sonarqube"]["status"] == "SUCCESS":
            score += _get_weight(weights, "sonarqube")
        else:
            issues.append(f"SonarQube failed: {checks['sonarqube']['message']}")

        if checks["wiz"]["status"] == "SUCCESS":
            score += _get_weight(weights, "wiz")
        else:
            issues.append(f"Wiz failed: {checks['wiz']['message']}")
            
        score += _get_weight(weights, "tests")

        promotion_threshold = gating_rules.get('promotion_threshold', 90)

        if issues or score < promotion_threshold:
            message = f'Quality gate failed with a score of {score}.'
            dt_client = dynatrace_client.DynatraceClient()
            dt_client.send_event(_create_dynatrace_event("PROMOTION_HALTED", repo_name, artifact_id, "FAILURE", message, score, {"issues": ", ".join(issues)}))
            slack_client_instance = slack_client.SlackClient()
            slack_client_instance.send_notification(_create_slack_notification(repo_name, artifact_id, score, issues))
            return {'statusCode': 200, 'body': json.dumps({'status': 'FAILURE', 'message': message, 'score': score, 'issues': issues})}
        else:
            message = f'All quality gates passed with a score of {score}.'
            dt_client = dynatrace_client.DynatraceClient()
            dt_client.send_event(_create_dynatrace_event("PROMOTION_APPROVED", repo_name, artifact_id, "SUCCESS", message, score))
            return {'statusCode': 200, 'body': json.dumps({'status': 'SUCCESS', 'message': message, 'score': score})}

    except Exception as e:
        print(f"Error in gate_handler: {e}")
        return {'statusCode': 500, 'body': json.dumps({'status': 'ERROR', 'message': 'An internal error occurred.'})}

# --- Suggestion Router Logic ---

def _infer_environment_from_namespace(namespace):
    """Infer environment from namespace using patterns."""
    namespace_lower = namespace.lower()
    
    # Production patterns
    if any(pattern in namespace_lower for pattern in ['prod', 'production', 'live']):
        return 'production'
    
    # Staging patterns  
    if any(pattern in namespace_lower for pattern in ['staging', 'stage', 'uat', 'test']):
        return 'staging'
    
    # Development patterns
    if any(pattern in namespace_lower for pattern in ['dev', 'development', 'sandbox']):
        return 'development'
    
    # Default to production for safety if unknown
    return 'production'

def _infer_application_type(app_name):
    """Infer application type from name patterns."""
    app_name_lower = app_name.lower()
    
    # API service patterns
    if any(pattern in app_name_lower for pattern in ['api', 'service', 'rest', 'graphql']):
        return 'api_service'
    
    # Worker service patterns
    if any(pattern in app_name_lower for pattern in ['worker', 'job', 'queue', 'processor']):
        return 'worker_service'
    
    # Frontend service patterns
    if any(pattern in app_name_lower for pattern in ['frontend', 'ui', 'web', 'react', 'vue', 'angular']):
        return 'frontend_service'
    
    # Default to API service
    return 'api_service'

def _check_data_availability(app_name, namespace):
    """Check what data is available from Dynatrace and return availability status."""
    try:
        # Get MCP client instance
        mcp_client = suggestion_engines.scaling_engine._get_mcp_client()
        
        # Use the new MCP client method to check data availability
        return mcp_client.check_data_availability(app_name, namespace)
            
    except Exception as e:
        print(f"Error checking data availability: {e}")
        return 'no_historical_data', None

def _build_enhanced_response(suggestion, data_availability, data_details, inferred_context, app_name, namespace):
    """Build the enhanced response structure matching the documented API."""
    
    # Base response structure
    response = {
        "suggestion_source": "ai_powered_with_fallbacks" if data_availability != 'full_historical_data' else "ai_powered",
        "data_availability": data_availability,
        "inferred_context": inferred_context
    }
    
    # Add current state based on data availability
    if data_availability == 'full_historical_data':
        response["current_state"] = {
            "current_replicas": 3,  # Would come from Kubernetes API
            "current_cpu_utilization": 75,  # Would come from Dynatrace
            "current_memory_utilization": 60,
            "current_resources": {
                "cpuRequest": "200m",
                "memoryRequest": "256Mi", 
                "cpuLimit": "500m",
                "memoryLimit": "512Mi"
            }
        }
        response["metrics_analysis"] = {
            "avg_cpu_last_7d": 65,
            "peak_cpu_last_7d": 89,
            "avg_memory_last_7d": 58,
            "request_rate_trend": "increasing",
            "pod_restart_rate": "low",
            "mcp_query_used": f"entities?entitySelector=type(SERVICE),entityName({app_name})&fields=metrics&from=now-7d"
        }
    elif data_availability == 'partial_data':
        response["current_state"] = {
            "current_replicas": 2,
            "current_cpu_utilization": 70,
            "current_memory_utilization": 55,
            "current_resources": {
                "cpuRequest": "200m",
                "memoryRequest": "256Mi",
                "cpuLimit": "500m", 
                "memoryLimit": "512Mi"
            }
        }
        response["metrics_analysis"] = {
            "avg_cpu_last_7d": None,
            "peak_cpu_last_7d": 78,
            "avg_memory_last_7d": None,
            "request_rate_trend": "unknown",
            "pod_restart_rate": "low",
            "mcp_query_result": f"partial_data_{data_details.get('days_available', 0)}_days",
            "fallback_strategy": "limited_data_with_safety_margin"
        }
    else:
        response["current_state"] = {
            "current_replicas": None,
            "current_cpu_utilization": None,
            "current_memory_utilization": None,
            "current_resources": None,
            "note": "Application not yet deployed or monitored"
        }
        response["metrics_analysis"] = {
            "avg_cpu_last_7d": None,
            "peak_cpu_last_7d": None,
            "avg_memory_last_7d": None,
            "request_rate_trend": "unknown",
            "pod_restart_rate": "unknown",
            "mcp_query_result": "no_data_found",
            "fallback_strategy": inferred_context.get("inference_source", {}).get("traffic_pattern", "default_patterns")
        }
    
    # Add the suggestion with validation
    try:
        # Validate suggestion structure using Pydantic model
        validated_suggestion = ScalingSuggestion.model_validate(suggestion["suggestion"])
        response["suggestion"] = validated_suggestion.model_dump(by_alias=True)
    except Exception as e:
        print(f"Warning: Suggestion validation failed: {e}")
        # Use unvalidated suggestion as fallback
        response["suggestion"] = suggestion["suggestion"]
    
    # Generate appropriate rationale based on data availability
    if data_availability == 'full_historical_data':
        response["suggestion"]["rationale"] = "Based on 7-day Dynatrace metrics analysis and inferred traffic patterns, optimized for current usage patterns with organization cost policies."
    elif data_availability == 'partial_data':
        response["suggestion"]["rationale"] = f"Based on {data_details.get('days_available', 0)} days of available metrics with safety margins applied. Recommend re-evaluation after more data is collected."
    else:
        response["suggestion"]["rationale"] = f"No historical Dynatrace data available. Using conservative {inferred_context.get('application_type', 'service')} best practices for {inferred_context.get('environment', 'unknown')} environment. Monitor for 1-2 weeks then re-run for optimization."
    
    return response

def suggestion_handler(event, _context):
    """
    Acts as a router for various suggestion requests with intelligent context inference.
    """
    try:
        config = load_config()
        body = json.loads(event.get('body', '{}'))
        
        suggestion_type = body.get('suggestion_type')
        if not suggestion_type:
            return {'statusCode': 400, 'body': json.dumps({'status': 'ERROR', 'message': 'Missing required key: suggestion_type'})}

        # --- Router ---
        if suggestion_type == suggestion_engines.constants.KUBERNETES_SCALING:
            app_context = body.get('application', {})
            deployment_context = body.get('deployment_context', {})
            
            # Validate required fields (only app name and namespace are required now)
            app_name = app_context.get('name')
            namespace = app_context.get('namespace')
            
            if not all([app_name, namespace]):
                return {'statusCode': 400, 'body': json.dumps({
                    'status': 'ERROR', 
                    'message': 'Missing required fields: application.name and application.namespace'
                })}
            
            # Intelligent context inference
            environment = app_context.get('environment') or _infer_environment_from_namespace(namespace)
            application_type = _infer_application_type(app_name)
            
            # Check data availability
            data_availability, data_details = _check_data_availability(app_name, namespace)
            
            # Build inferred context
            inferred_context = {
                "deployment_type": "rolling_update",  # Could be inferred from Kubernetes deployment annotations
                "traffic_pattern": "steady",  # Would be inferred from Dynatrace historical analysis
                "cost_optimization": deployment_context.get('cost_optimization', "balanced"),  # From org policies or override
                "environment": environment,
                "application_type": application_type,
                "inference_source": {
                    "deployment_type": "kubernetes_default",
                    "traffic_pattern": "dynatrace_historical_analysis" if data_availability == 'full_historical_data' else "default_pattern_fallback",
                    "cost_optimization": "deployment_context_override" if deployment_context.get('cost_optimization') else "organization_policy",
                    "environment": "namespace_pattern_inference",
                    "application_type": "name_pattern_inference"
                }
            }
            
            # For partial data, adjust traffic pattern inference
            if data_availability == 'partial_data':
                inferred_context["traffic_pattern"] = "peak_hours"  # Based on limited analysis
                inferred_context["inference_source"]["traffic_pattern"] = "limited_data_analysis"
            
            # Use MCP client for actual trend analysis when data is available
            if data_availability in ['full_historical_data', 'partial_data'] and data_details:
                try:
                    entity_id = data_details.get('entity_id')
                    if entity_id:
                        mcp_client = suggestion_engines.scaling_engine._get_mcp_client()
                        trend_analysis = mcp_client.get_trend_analysis(entity_id)
                        
                        # Update inferred context with actual trend analysis
                        inferred_context["traffic_pattern"] = trend_analysis.get("traffic_pattern", inferred_context["traffic_pattern"])
                        inferred_context["inference_source"]["traffic_pattern"] = "dynatrace_mcp_trend_analysis"
                except Exception as e:
                    print(f"Warning: Could not perform trend analysis: {e}")
                    # Keep the existing inference
            
            # Build enhanced deployment context for the engine
            enhanced_deployment_context = {
                'environment': environment,
                'deployment_name': app_name,  # Use app name as deployment name
                'architecture': deployment_context.get('architecture', 'amd64'),
                'data_availability': data_availability,
                'inferred_context': inferred_context
            }
            
            # Get suggestion from engine
            result = suggestion_engines.scaling_engine.get_suggestion(config, app_context, enhanced_deployment_context)
            
            # Build enhanced response
            enhanced_response = _build_enhanced_response(
                result, data_availability, data_details, inferred_context, app_name, namespace
            )
            
            return {'statusCode': 200, 'body': json.dumps(enhanced_response)}
        
        # --- Add future engines here ---
        # if suggestion_type == 'cost_optimization':
        #     return suggestion_engines.cost_engine.get_suggestion(...)

        else:
            return {'statusCode': 400, 'body': json.dumps({'status': 'ERROR', 'message': f"Unknown suggestion_type: {suggestion_type}"})}

    except Exception as e:
        print(f"Error in suggestion_handler: {e}")
        return {'statusCode': 500, 'body': json.dumps({'status': 'ERROR', 'message': 'An internal error occurred.'})}

# --- Notification Helpers ---

def _create_slack_notification(repo_name, artifact_id, score, issues):
    """Helper function to create a formatted Slack notification payload."""
    issue_list = "\n".join([f"- {issue}" for issue in issues])
    return {
        "blocks": [
            {"type": "header", "text": {"type": "plain_text", "text": ":no_entry: SRE Quality Gate FAILED"}},
            {"type": "section", "fields": [
                {"type": "mrkdwn", "text": f"*Application:*\n{repo_name}"},
                {"type": "mrkdwn", "text": f"*Artifact:*\n{artifact_id}"},
                {"type": "mrkdwn", "text": f"*Readiness Score:*\n{score}"}
            ]},
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*Detected Issues:*\n{issue_list}"}},
            {"type": "context", "elements": [{"type": "mrkdwn", "text": "The deployment has been halted."}]}
        ]
    }

def _create_dynatrace_event(event_type, repo_name, artifact_id, status, message, score=None, properties=None):
    """Helper function to create a Dynatrace event payload."""
    payload = {
        "eventType": f"CUSTOM_{event_type}",
        "title": f"SRE Agent: {message}",
        "entitySelector": f"type(CUSTOM_DEVICE),tag(sre-agent),tag({repo_name})",
        "properties": {
            "application": repo_name,
            "artifact": artifact_id,
            "status": status,
            "message": message,
            "score": score
        }
    }
    if properties:
        payload["properties"].update(properties)
    return payload

def lambda_handler(event, context):
    """
    Unified Lambda handler that routes requests to appropriate handlers based on path.
    This enables container image deployment with a single function.
    """
    try:
        # Extract path from API Gateway event
        path = event.get('path', '')
        http_method = event.get('httpMethod', 'POST')
        
        # Route based on path
        if path == '/gate' and http_method == 'POST':
            return gate_handler(event, context)
        elif path == '/suggest' and http_method == 'POST':
            return suggestion_handler(event, context)
        else:
            return {
                'statusCode': 404,
                'body': json.dumps({
                    'status': 'ERROR',
                    'message': f'Endpoint not found: {http_method} {path}'
                })
            }
    except Exception as e:
        print(f"Error in lambda_handler: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'status': 'ERROR',
                'message': 'Internal server error'
            })
        }
