"""This module contains the logic for the scaling suggestion engine."""
import os
import json
import sys
from typing import Dict, Any, Optional
from ..llm_client import OllamaClient, BringYourOwnLLMClient
from ..mcp_client import DynatraceMCPClient, MockMCPClient
from ..data_models import ScalingSuggestionContent

# Import the tools utility using absolute import
from ..utils.llm_tools import create_scaling_tools_manager


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
2. If data exists, discover the entity ID and gather historical
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
            final_config['resource_sizing'] = {
                **final_config.get('resource_sizing', {}),
                **env_override['resource_sizing']
            }
        if 'scaling_configuration' in env_override:
            final_config['scaling_configuration'] = {
                **final_config.get('scaling_configuration', {}),
                **env_override['scaling_configuration']
            }
    
    # Layer 3: Application type patterns
    app_pattern = app_type_patterns.get(application_type, {})
    if app_pattern:
        if 'resource_sizing' in app_pattern:
            final_config['resource_sizing'] = {
                **final_config.get('resource_sizing', {}),
                **app_pattern['resource_sizing']
            }
        if 'scaling_configuration' in app_pattern:
            final_config['scaling_configuration'] = {
                **final_config.get('scaling_configuration', {}),
                **app_pattern['scaling_configuration']
            }
    
    # Layer 4: Cost optimization policies
    cost_policy = org_policies.get('cost_optimization', {}).get(cost_optimization, {})
    if cost_policy:
        if 'resource_sizing' in cost_policy:
            final_config['resource_sizing'] = {
                **final_config.get('resource_sizing', {}),
                **cost_policy['resource_sizing']
            }
        if 'scaling_configuration' in cost_policy:
            final_config['scaling_configuration'] = {
                **final_config.get('scaling_configuration', {}),
                **cost_policy['scaling_configuration']
            }
    
    # Convert to the expected format
    hpa_config = final_config.get('scaling_configuration', {}).get('hpa', {})
    karpenter_config = final_config.get('scaling_configuration', {}).get('karpenter', {})
    
    hpa_suggestion = {
        "minReplicas": hpa_config.get('min_replicas', 1),
        "maxReplicas": hpa_config.get('max_replicas', 3),
        "targetCPUUtilizationPercentage": hpa_config.get('cpu_utilization_target', 70),
        "scaleTargetRefName": deployment_context.get('deployment_name', repo_name)
    }
    
    karpenter_suggestion = {
        "kubernetes.io/arch": karpenter_config.get('architecture', 'amd64'),
        "karpenter.sh/capacity-type": karpenter_config.get('capacity_type', 'on-demand')
    }
    
    return {"hpa": hpa_suggestion, "karpenter": karpenter_suggestion}

def _run_ai_suggestion_workflow(app_context, deployment_context, config):
    """Run the AI-powered suggestion workflow."""
    llm_client = _get_llm_client()
    mcp_client = _get_mcp_client()
    
    # Prepare context
    app_name = app_context.get('name')
    namespace = deployment_context.get('environment', 'default')
    target_entity = f"{app_name}:{namespace}"
    
    # Create tools manager with validation schema
    tools_manager = create_scaling_tools_manager(
        mcp_client, 
        ScalingSuggestionContent.model_json_schema()
    )
    
    # Initialize conversation
    tools = tools_manager.get_tools_for_llm()
    messages = [{"role": "user", "content": _build_initial_prompt(target_entity, app_name, namespace)}]
    
    # Execute conversation loop
    max_iterations = 5
    for iteration in range(max_iterations):
        try:
            # Get LLM response
            llm_response = llm_client.call(messages, tools)
            
            # Check if LLM made tool calls
            if not llm_response.get("tool_calls"):
                break
            
            # Add assistant response to conversation history
            messages.append(llm_response)
            
            # Execute tool calls
            for tool_call in llm_response["tool_calls"]:
                function_name = tool_call['function']['name']
                function_args = json.loads(tool_call['function']['arguments'])
                
                # Execute tool using tools manager
                try:
                    tool_result = tools_manager.execute_tool(function_name, **function_args)
                    
                    # Check if we got a final suggestion
                    if isinstance(tool_result, dict) and "suggestion" in tool_result:
                        return tool_result
                    
                    # Add tool result to conversation history
                    messages.append({
                                "tool_call_id": tool_call['id'],
                                "role": "tool",
                                "name": function_name,
                        "content": json.dumps(tool_result)
                            })
                    
                except Exception as e:
                    print(f"Error executing tool {function_name}: {e}")
                    messages.append({
                                "tool_call_id": tool_call['id'],
                                "role": "tool",
                                "name": function_name,
                        "content": f"Error: {str(e)}"
                            })
                    
        except Exception as e:
            print(f"Error in AI workflow iteration {iteration}: {e}")
            break
    
    # If we reach here, AI workflow didn't produce a valid suggestion
    return None

def get_suggestion(config, app_context, deployment_context):
    """
    Generates a scaling suggestion using AI-first approach with static fallback.
    
    Args:
        config: Configuration dictionary from AppConfig
        app_context: Application context (name, namespace, etc.)
        deployment_context: Deployment context (environment, etc.)
    
    Returns:
        dict: Scaling suggestion with source information
    """
    # Generate static fallback suggestion first
    static_suggestion = _generate_static_suggestion(
        deployment_context, app_context.get('name'), config
    )
    
    # Check if AI is enabled
    enable_ai = config.get('features', {}).get('enable_ai_shadow_analyst', False)
    if not enable_ai:
        print("AI suggestion disabled, using static fallback.")
        return {
            'suggestion': static_suggestion, 
            'suggestion_source': 'static'
        }
    
    # Try AI-powered suggestion
    try:
        ai_result = _run_ai_suggestion_workflow(app_context, deployment_context, config)
        if ai_result:
            print("AI suggestion generated successfully.")
            return ai_result
    except Exception as e:
        print(f"AI suggestion workflow failed: {e}")
    
    # Fall back to static suggestion
    print("Using static suggestion as fallback.")
    return {
        'suggestion': static_suggestion, 
        'suggestion_source': 'static'
    }
