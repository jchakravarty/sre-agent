"""
LLM Tools Utility Module

This module provides an abstraction layer for defining and managing LLM tools
used by the AI suggestion engine. It supports dynamic tool registration,
validation, and execution.
"""

import json
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass
from enum import Enum


class ToolType(Enum):
    """Enumeration of supported tool types."""
    FUNCTION = "function"
    QUERY = "query"
    ANALYSIS = "analysis"
    SUBMISSION = "submission"


@dataclass
class ToolParameter:
    """Represents a tool parameter with validation."""
    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None
    enum_values: Optional[List[str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for LLM tools."""
        param_dict: Dict[str, Any] = {
            "type": self.type,
            "description": self.description,
        }
        
        # Only add 'required' field if it's False (True is the default assumption)
        if not self.required:
            param_dict["required"] = False
            
        # Add default value if provided
        if self.default is not None:
            param_dict["default"] = self.default
            
        # Add enum values if provided
        if self.enum_values is not None and len(self.enum_values) > 0:
            param_dict["enum"] = self.enum_values
            
        return param_dict


@dataclass
class ToolDefinition:
    """Represents a complete tool definition."""
    name: str
    description: str
    tool_type: ToolType
    parameters: List[ToolParameter]
    handler: Optional[Callable] = None
    
    def to_llm_format(self) -> Dict[str, Any]:
        """Convert to LLM-compatible format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        param.name: param.to_dict() 
                        for param in self.parameters
                    },
                    "required": [
                        param.name 
                        for param in self.parameters 
                        if param.required
                    ]
                }
            }
        }


class ToolRegistry:
    """Registry for managing LLM tools."""
    
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._handlers: Dict[str, Callable] = {}
    
    def register_tool(self, tool: ToolDefinition) -> None:
        """Register a tool in the registry."""
        self._tools[tool.name] = tool
        if tool.handler:
            self._handlers[tool.name] = tool.handler
    
    def register_handler(self, tool_name: str, handler: Callable) -> None:
        """Register a handler for an existing tool."""
        if tool_name in self._tools:
            self._handlers[tool_name] = handler
    
    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        """Get a tool by name."""
        return self._tools.get(name)
    
    def get_handler(self, name: str) -> Optional[Callable]:
        """Get a handler by tool name."""
        return self._handlers.get(name)
    
    def list_tools(self) -> List[str]:
        """List all registered tool names."""
        return list(self._tools.keys())
    
    def get_all_tools_llm_format(self) -> List[Dict[str, Any]]:
        """Get all tools in LLM-compatible format."""
        return [tool.to_llm_format() for tool in self._tools.values()]
    
    def execute_tool(self, tool_name: str, **kwargs) -> Any:
        """Execute a tool with given parameters."""
        handler = self.get_handler(tool_name)
        if not handler:
            raise ValueError(f"No handler registered for tool: {tool_name}")
        return handler(**kwargs)


class BaseToolHandler(ABC):
    """Abstract base class for tool handlers."""
    
    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """Execute the tool with given parameters."""
        pass
    
    @abstractmethod
    def validate_parameters(self, **kwargs) -> bool:
        """Validate tool parameters."""
        pass


class ScalingToolsFactory:
    """Factory for creating scaling-related tools."""
    
    @staticmethod
    def create_performance_metrics_tool() -> ToolDefinition:
        """Create performance metrics tool."""
        return ToolDefinition(
            name="get_performance_metrics",
            description="Gets key performance metrics for a service.",
            tool_type=ToolType.QUERY,
            parameters=[
                ToolParameter(
                    name="entity_id",
                    type="string",
                    description="The ID of the service to query.",
                    required=True
                )
            ]
        )
    
    @staticmethod
    def create_health_events_tool() -> ToolDefinition:
        """Create health events tool."""
        return ToolDefinition(
            name="get_health_events",
            description="Gets health events (e.g., problems, OOM kills) for a service.",
            tool_type=ToolType.QUERY,
            parameters=[
                ToolParameter(
                    name="entity_id",
                    type="string",
                    description="The ID of the service to query.",
                    required=True
                )
            ]
        )
    
    @staticmethod
    def create_slo_tool() -> ToolDefinition:
        """Create SLO tool."""
        return ToolDefinition(
            name="get_service_level_objectives",
            description="Gets the status of all SLOs related to a service.",
            tool_type=ToolType.QUERY,
            parameters=[
                ToolParameter(
                    name="entity_id",
                    type="string",
                    description="The ID of the service to query.",
                    required=True
                )
            ]
        )
    
    @staticmethod
    def create_data_availability_tool() -> ToolDefinition:
        """Create data availability tool."""
        return ToolDefinition(
            name="check_data_availability",
            description="Check what historical data is available for an application.",
            tool_type=ToolType.QUERY,
            parameters=[
                ToolParameter(
                    name="app_name",
                    type="string",
                    description="The application name.",
                    required=True
                ),
                ToolParameter(
                    name="namespace",
                    type="string",
                    description="The Kubernetes namespace.",
                    required=True
                )
            ]
        )
    
    @staticmethod
    def create_entity_discovery_tool() -> ToolDefinition:
        """Create entity discovery tool."""
        return ToolDefinition(
            name="discover_entity",
            description="Discover the Dynatrace entity ID for an application.",
            tool_type=ToolType.QUERY,
            parameters=[
                ToolParameter(
                    name="app_name",
                    type="string",
                    description="The application name.",
                    required=True
                ),
                ToolParameter(
                    name="namespace",
                    type="string",
                    description="The Kubernetes namespace.",
                    required=True
                )
            ]
        )
    
    @staticmethod
    def create_historical_metrics_tool() -> ToolDefinition:
        """Create historical metrics tool."""
        return ToolDefinition(
            name="get_historical_metrics",
            description="Get historical metrics for trend analysis over specified days.",
            tool_type=ToolType.QUERY,
            parameters=[
                ToolParameter(
                    name="entity_id",
                    type="string",
                    description="The Dynatrace entity ID.",
                    required=True
                ),
                ToolParameter(
                    name="days",
                    type="integer",
                    description="Number of days to analyze (default: 7)",
                    required=False,
                    default=7
                )
            ]
        )
    
    @staticmethod
    def create_trend_analysis_tool() -> ToolDefinition:
        """Create trend analysis tool."""
        return ToolDefinition(
            name="get_trend_analysis",
            description="Analyze metrics trends to infer traffic patterns and scaling needs.",
            tool_type=ToolType.ANALYSIS,
            parameters=[
                ToolParameter(
                    name="entity_id",
                    type="string",
                    description="The Dynatrace entity ID.",
                    required=True
                ),
                ToolParameter(
                    name="days",
                    type="integer",
                    description="Number of days to analyze (default: 7)",
                    required=False,
                    default=7
                )
            ]
        )
    
    @staticmethod
    def create_scaling_submission_tool(schema: Optional[Dict[str, Any]] = None) -> ToolDefinition:
        """Create scaling submission tool."""
        # Create a generic submission tool that can work with any schema
        parameters = [
            ToolParameter(
                name="hpa",
                type="object",
                description="HPA configuration with minReplicas, maxReplicas, targetCPUUtilizationPercentage",
                required=True
            ),
            ToolParameter(
                name="resources",
                type="object", 
                description="Resource configuration with cpu_request, memory_request, cpu_limit, memory_limit",
                required=True
            ),
            ToolParameter(
                name="ai_rationale",
                type="string",
                description="Detailed explanation of the scaling recommendation",
                required=True
            ),
            ToolParameter(
                name="confidence_score",
                type="number",
                description="Confidence score between 0 and 1",
                required=False,
                default=0.8
            )
        ]
        
        return ToolDefinition(
            name="submit_scaling_suggestion",
            description="Submits the final proposed scaling suggestion with rationale.",
            tool_type=ToolType.SUBMISSION,
            parameters=parameters
        )


class ScalingToolsManager:
    """Manager for scaling-related tools with MCP client integration."""
    
    def __init__(self, mcp_client, validation_schema: Optional[Dict[str, Any]] = None):
        self.mcp_client = mcp_client
        self.validation_schema = validation_schema
        self.registry = ToolRegistry()
        self._register_default_tools()
    
    def _register_default_tools(self) -> None:
        """Register all default scaling tools."""
        factory = ScalingToolsFactory()
        
        # Register tools with their handlers
        tools = [
            (factory.create_performance_metrics_tool(), self._handle_performance_metrics),
            (factory.create_health_events_tool(), self._handle_health_events),
            (factory.create_slo_tool(), self._handle_slo),
            (factory.create_data_availability_tool(), self._handle_data_availability),
            (factory.create_entity_discovery_tool(), self._handle_entity_discovery),
            (factory.create_historical_metrics_tool(), self._handle_historical_metrics),
            (factory.create_trend_analysis_tool(), self._handle_trend_analysis),
        ]
        
        for tool, handler in tools:
            tool.handler = handler
            self.registry.register_tool(tool)
        
        # Register submission tool
        submission_tool = factory.create_scaling_submission_tool(self.validation_schema)
        submission_tool.handler = self._handle_scaling_submission
        self.registry.register_tool(submission_tool)
    
    def get_tools_for_llm(self) -> List[Dict[str, Any]]:
        """Get all tools in LLM-compatible format."""
        return self.registry.get_all_tools_llm_format()
    
    def execute_tool(self, tool_name: str, **kwargs) -> Any:
        """Execute a tool by name."""
        return self.registry.execute_tool(tool_name, **kwargs)
    
    # Tool handlers
    def _handle_performance_metrics(self, entity_id: str) -> Dict[str, Any]:
        """Handle performance metrics tool call."""
        return self.mcp_client.get_performance_metrics(entity_id)
    
    def _handle_health_events(self, entity_id: str) -> Dict[str, Any]:
        """Handle health events tool call."""
        return self.mcp_client.get_health_events(entity_id)
    
    def _handle_slo(self, entity_id: str) -> Dict[str, Any]:
        """Handle SLO tool call."""
        return self.mcp_client.get_service_level_objectives(entity_id)
    
    def _handle_data_availability(self, app_name: str, namespace: str) -> Dict[str, Any]:
        """Handle data availability tool call."""
        status, details = self.mcp_client.check_data_availability(app_name, namespace)
        return {"status": status, "details": details}
    
    def _handle_entity_discovery(self, app_name: str, namespace: str) -> Dict[str, Any]:
        """Handle entity discovery tool call."""
        entity_id = self.mcp_client.discover_entity(app_name, namespace)
        return {"entity_id": entity_id} if entity_id else {"entity_id": None}
    
    def _handle_historical_metrics(self, entity_id: str, days: int = 7) -> Dict[str, Any]:
        """Handle historical metrics tool call."""
        return self.mcp_client.get_historical_metrics(entity_id, days)
    
    def _handle_trend_analysis(self, entity_id: str, days: int = 7) -> Dict[str, Any]:
        """Handle trend analysis tool call."""
        return self.mcp_client.get_trend_analysis(entity_id, days)
    
    def _handle_scaling_submission(self, **kwargs) -> Dict[str, Any]:
        """Handle scaling submission tool call."""
        # Create a basic validated response without importing data_models
        suggestion_data = {
            "hpa": kwargs.get("hpa", {}),
            "resources": kwargs.get("resources", {}),
            "ai_rationale": kwargs.get("ai_rationale", ""),
            "confidence_score": kwargs.get("confidence_score", 0.8)
        }
        
        return {
            "suggestion": suggestion_data,
            "suggestion_source": "llm_validated"
        }


# Convenience functions for easy usage
def create_scaling_tools_manager(mcp_client, validation_schema: Optional[Dict[str, Any]] = None) -> ScalingToolsManager:
    """Create a scaling tools manager with default tools."""
    return ScalingToolsManager(mcp_client, validation_schema)


def get_default_scaling_tools(mcp_client, validation_schema: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Get default scaling tools in LLM format."""
    manager = create_scaling_tools_manager(mcp_client, validation_schema)
    return manager.get_tools_for_llm() 