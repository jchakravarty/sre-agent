"""This module contains the base class for MCP clients."""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Tuple

class MCPClient(ABC):
    """Base class for MCP clients."""
    
    @abstractmethod
    def get_scaling_context(self, entity_id):
        """Gets the scaling context for a given entity."""
        pass

    @abstractmethod
    def check_data_availability(self, app_name: str, namespace: str) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        Check what historical data is available for an application.
        
        Returns:
            Tuple of (availability_status, data_details)
            availability_status: 'full_historical_data', 'partial_data', or 'no_historical_data'
            data_details: Dict with details like days_available, completeness, etc.
        """
        pass
    
    @abstractmethod
    def discover_entity(self, app_name: str, namespace: str) -> Optional[str]:
        """
        Discover the Dynatrace entity ID for an application by name and namespace.
        
        Returns:
            Entity ID if found, None if not found
        """
        pass
    
    @abstractmethod
    def get_historical_metrics(self, entity_id: str, days: int = 7) -> Dict[str, Any]:
        """
        Get historical metrics for trend analysis.
        
        Returns:
            Dict containing averaged metrics over the specified period
        """
        pass
    
    @abstractmethod
    def get_trend_analysis(self, entity_id: str, days: int = 7) -> Dict[str, Any]:
        """
        Analyze metrics trends over time to infer traffic patterns.
        
        Returns:
            Dict containing trend analysis results
        """
        pass
