"""This module contains the logic for the scaling suggestion engine."""
import os
import json
from ..llm_client import OllamaClient, BringYourOwnLLMClient
from ..mcp_client import DynatraceMCPClient, MockMCPClient
from ..data_models import ScalingSuggestion, ScalingSuggestionContent

# --- Client Factories ---

def _get_mcp_client():
    """Factory to get the configured MCP client."""
    client_type = os.environ.get("MCP_CLIENT_TYPE", "dynatrace").lower()
    if client_type == "mock":
        print("Using MockMCPClient for Scaling Engine")
        return MockMCPClient()
    print("Using DynatraceMCPClient for Scaling Engine")
    return DynatraceMCPClient()

def _get_llm_client():
    """Factory to get the configured LLM client."""
    client_type = os.environ.get("LLM_CLIENT_TYPE", "ollama").lower()
    if client_type == "byo":
        api_key = os.environ.get("BYO_LLM_API_KEY")
        api_endpoint = os.environ.get("BYO_LLM_API_ENDPOINT")
        if not all([api_key, api_endpoint]):
            raise ValueError(
                "BYO_LLM_API_KEY and BYO_LLM_API_ENDPOINT must be set for 'byo' client type."
            )
        return BringYourOwnLLMClient(api_key, api_endpoint)
    return OllamaClient()

# --- AI Suggestion Logic ---

def _build_initial_prompt(target_entity, app_name, namespace):
    """Builds the initial prompt to kick off the conversation with the LLM."""
    return f"""
You are an expert Kubernetes SRE. Your task is to generate an optimal scaling configuration for the service '{target_entity}' (app: {app_name}, namespace: {namespace}).

Available tools:
1. check_data_availability - Check what historical data exists for this application
2. discover_entity - Find the Dynatrace entity ID for the application
3. get_historical_metrics - Get 7-day metrics history for trend analysis
4. get_trend_analysis - Analyze traffic patterns and scaling trends
5. get_performance_metrics - Get current performance metrics
6. get_health_events - Get health events and problems
7. get_service_level_objectives - Get SLO status

Strategy:
1. Start by checking data availability for {app_name} in {namespace}
2. If data exists, discover the entity ID and gather historical metrics
3. Analyze trends to understand traffic patterns (steady, peak hours, growth, etc.)
4. Get current performance and health data
5. Based on all information, generate an optimal scaling configuration with detailed rationale

Always include a comprehensive rationale explaining your reasoning based on the data you gathered.
"""

def _generate_static_suggestion(deployment_context, repo_name, config):
    """Generates scaling parameters based on a layered configuration with intelligent fallbacks."""
    env_name = deployment_context.get('environment', '').lower()
    data_availability = deployment_context.get('data_availability', 'full_historical_data')
    inferred_context = deployment_context.get('inferred_context', {})
    
    # Get fallback configuration from AWS AppConfig
    fallback_config = config.get('fallback_strategies', {})
    environment_defaults = config.get('environment_defaults', {})
    app_type_patterns = config.get('application_type_patterns', {})
    org_policies = config.get('organization_policies', {})
    
    # Determine which fallback strategy to use
    if data_availability == 'no_historical_data':
        base_fallback = fallback_config.get('new_deployment', {})
    elif data_availability == 'partial_data':
        base_fallback = fallback_config.get('partial_data', {})
    else:
        # Use existing scaling_suggestions for backward compatibility
        scaling_configs = config.get('scaling_suggestions', {})
        base_config = {}
        env_configs = scaling_configs.get('environments', {})
        for key, cfg in env_configs.items():
            aliases = [alias.lower() for alias in cfg.get('aliases', [])]
            if env_name == key.lower() or env_name in aliases:
                base_config = cfg
                break

        app_overrides = scaling_configs.get('applications', {}).get(repo_name, {})
        env_override = app_overrides.get(env_name, {})

        final_hpa = {
            **base_config.get('hpa', {}),
            **env_override.get('hpa', {})
        }
        final_karpenter = {
            **base_config.get('karpenter', {}),
            **env_override.get('karpenter', {})
        }

        hpa_suggestion = {
            "minReplicas": final_hpa.get('min_replicas'),
            "maxReplicas": final_hpa.get('max_replicas'),
            "targetCPUUtilizationPercentage": final_hpa.get('cpu_utilization_target'),
            "scaleTargetRefName": deployment_context.get('deployment_name')
        }
        karpenter_suggestion = {
            "kubernetes.io/arch": deployment_context.get('architecture'),
            "karpenter.sh/capacity-type": final_karpenter.get('capacity_type')
        }

        return {"hpa": hpa_suggestion, "karpenter": karpenter_suggestion}
    
    # Apply intelligent fallback strategy
    application_type = inferred_context.get('application_type', 'api_service')
    cost_optimization = inferred_context.get('cost_optimization', 'balanced')
    
    # Start with base fallback configuration
    final_config = {}
    
    # Layer 1: Base fallback (new_deployment or partial_data)
    if base_fallback:
        final_config = {
            'resource_sizing': base_fallback.get('resource_sizing', {}),
            'scaling_configuration': base_fallback.get('scaling_configuration', {}),
            'infrastructure': base_fallback.get('infrastructure', {})
        }
    
    # Layer 2: Environment-specific overrides
    env_override = environment_defaults.get(env_name, {})
    if env_override:
        if 'resource_sizing' in env_override:
            final_config.setdefault('resource_sizing', {}).update(env_override['resource_sizing'])
        if 'scaling_configuration' in env_override:
            final_config.setdefault('scaling_configuration', {}).update(env_override['scaling_configuration'])
        if 'infrastructure' in env_override:
            final_config.setdefault('infrastructure', {}).update(env_override['infrastructure'])
    
    # Layer 3: Application type patterns
    app_type_config = app_type_patterns.get(application_type, {})
    if app_type_config:
        if 'scaling_configuration' in app_type_config:
            final_config.setdefault('scaling_configuration', {}).update(app_type_config['scaling_configuration'])
        if 'resource_sizing' in app_type_config:
            final_config.setdefault('resource_sizing', {}).update(app_type_config['resource_sizing'])
    
    # Layer 4: Organization cost policies
    cost_policy = org_policies.get('cost_optimization', {}).get(cost_optimization, {})
    if cost_policy:
        # Apply cost policy to infrastructure
        infrastructure = final_config.setdefault('infrastructure', {})
        if 'capacity_type' in cost_policy:
            infrastructure['capacity_type'] = cost_policy['capacity_type']
        if 'target_cpu' in cost_policy:
            final_config.setdefault('scaling_configuration', {})['target_cpu'] = cost_policy['target_cpu']
    
    # Build the final suggestion in the expected format
    resource_sizing = final_config.get('resource_sizing', {})
    scaling_config = final_config.get('scaling_configuration', {})
    infrastructure = final_config.get('infrastructure', {})
    
    hpa_suggestion = {
        "minReplicas": scaling_config.get('min_replicas', 2),
        "maxReplicas": scaling_config.get('max_replicas', 6),
        "targetCPUUtilizationPercentage": scaling_config.get('target_cpu', 70),
        "scaleTargetRefName": deployment_context.get('deployment_name'),
        "resources": {
            "cpuLimit": resource_sizing.get('cpu_limit', "500m"),
            "memoryLimit": resource_sizing.get('memory_limit', "512Mi"),
            "cpuRequest": resource_sizing.get('cpu_request', "250m"),
            "memoryRequest": resource_sizing.get('memory_request', "256Mi")
        }
    }
    
    karpenter_suggestion = {
        "kubernetes.io/arch": infrastructure.get('arch', deployment_context.get('architecture', 'amd64')),
        "karpenter.sh/capacity-type": infrastructure.get('capacity_type', 'spot')
    }

    # Validate the suggestion using Pydantic models for consistency
    try:
        suggestion_data = {"hpa": hpa_suggestion, "karpenter": karpenter_suggestion}
        validated_suggestion = ScalingSuggestion.model_validate(suggestion_data)
        return {"hpa": validated_suggestion.hpa.model_dump(by_alias=True), 
                "karpenter": validated_suggestion.karpenter.model_dump(by_alias=True)}
    except Exception as e:
        print(f"Warning: Static suggestion validation failed: {e}")
        # Return unvalidated suggestion as fallback
        return {"hpa": hpa_suggestion, "karpenter": karpenter_suggestion}

def get_suggestion(config, app_context, deployment_context):
    """
    Generates a scaling suggestion, using an AI-first approach with a static fallback.
    """
    static_suggestion = _generate_static_suggestion(
        deployment_context, app_context.get('name'), config
    )

    enable_ai = config.get('features', {}).get('enable_ai_shadow_analyst', False)
    if enable_ai:
        try:
            llm_client = _get_llm_client()
            mcp_client = _get_mcp_client()
            target_entity = f"{app_context.get('name')}:{deployment_context.get('environment')}"
            
            # Define the tools available to the LLM
            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "get_performance_metrics",
                        "description": "Gets key performance metrics for a service.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "entity_id": {"type": "string", "description": "The ID of the service to query."}
                            },
                            "required": ["entity_id"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "get_health_events",
                        "description": "Gets health events (e.g., problems, OOM kills) for a service.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "entity_id": {"type": "string", "description": "The ID of the service to query."}
                            },
                            "required": ["entity_id"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "get_service_level_objectives",
                        "description": "Gets the status of all SLOs related to a service.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "entity_id": {"type": "string", "description": "The ID of the service to query."}
                            },
                            "required": ["entity_id"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "check_data_availability",
                        "description": "Check what historical data is available for an application.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "app_name": {"type": "string", "description": "The application name."},
                                "namespace": {"type": "string", "description": "The Kubernetes namespace."}
                            },
                            "required": ["app_name", "namespace"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "discover_entity",
                        "description": "Discover the Dynatrace entity ID for an application.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "app_name": {"type": "string", "description": "The application name."},
                                "namespace": {"type": "string", "description": "The Kubernetes namespace."}
                            },
                            "required": ["app_name", "namespace"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "get_historical_metrics",
                        "description": "Get historical metrics for trend analysis over specified days.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "entity_id": {"type": "string", "description": "The Dynatrace entity ID."},
                                "days": {"type": "integer", "description": "Number of days to analyze (default: 7)", "default": 7}
                            },
                            "required": ["entity_id"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "get_trend_analysis",
                        "description": "Analyze metrics trends to infer traffic patterns and scaling needs.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "entity_id": {"type": "string", "description": "The Dynatrace entity ID."},
                                "days": {"type": "integer", "description": "Number of days to analyze (default: 7)", "default": 7}
                            },
                            "required": ["entity_id"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "submit_scaling_suggestion",
                        "description": "Submits the final proposed scaling suggestion with rationale.",
                        "parameters": ScalingSuggestionContent.model_json_schema()
                    }
                }
            ]
            
            app_name = app_context.get('name')
            namespace = deployment_context.get('environment', 'default')
            messages = [{"role": "user", "content": _build_initial_prompt(target_entity, app_name, namespace)}]
            
            # Orchestration loop
            for _ in range(5): # Limit the number of turns to prevent infinite loops
                llm_response = llm_client.call(messages, tools)
                
                if llm_response.get("tool_calls"):
                    tool_calls = llm_response["tool_calls"]
                    messages.append(llm_response) # Add the assistant's response to the history
                    
                    for tool_call in tool_calls:
                        function_name = tool_call['function']['name']
                        function_args = json.loads(tool_call['function']['arguments'])
                        
                        if function_name == 'submit_scaling_suggestion':
                            validated_suggestion = ScalingSuggestionContent.model_validate(function_args)
                            return {
                                "suggestion": validated_suggestion.model_dump(by_alias=True),
                                "suggestion_source": "llm_validated"
                            }
                        
                        # Dispatch to the appropriate MCP client method
                        if hasattr(mcp_client, function_name):
                            function_to_call = getattr(mcp_client, function_name)
                            tool_output = function_to_call(**function_args)
                            messages.append({
                                "tool_call_id": tool_call['id'],
                                "role": "tool",
                                "name": function_name,
                                "content": json.dumps(tool_output)
                            })
                        else:
                             messages.append({
                                "tool_call_id": tool_call['id'],
                                "role": "tool",
                                "name": function_name,
                                "content": "Error: Tool not found."
                            })
                else:
                    # If the LLM doesn't make a tool call, break the loop
                    break
                    
        except Exception as e:
            print(f"Error in LLM suggestion workflow: {e}")

    print("Using static suggestion as fallback.")
    return {'suggestion': static_suggestion, 'suggestion_source': 'static'}
