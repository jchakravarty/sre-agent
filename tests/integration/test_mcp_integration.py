#!/usr/bin/env python3
"""Test script to verify MCP client integration with enhanced API."""

import sys
import os
sys.path.append('src')

def test_mcp_client_integration():
    """Test that the updated MCP client integrates correctly."""
    
    print("🔍 Testing MCP Client Integration...")
    
    # Import MCP clients
    from src.mcp_client.mock_mcp_client import MockMCPClient
    from src.mcp_client.dynatrace_mcp_client import DynatraceMCPClient
    print("✅ MCP client imports successful")
    
    # Test MockMCPClient with enhanced methods
    mock_client = MockMCPClient()
    
    # Test data availability checking
    availability, details = mock_client.check_data_availability("user-service", "production")
    print(f"✅ Data availability check: {availability}")
    assert availability in ['full_historical_data', 'partial_data', 'no_historical_data']
    if details:
        print(f"   📊 Details: {details['days_available']} days, {details['completeness']}% complete")
        assert 'days_available' in details
        assert 'completeness' in details
    
    # Test entity discovery
    entity_id = mock_client.discover_entity("payment-service", "staging")
    print(f"✅ Entity discovery: {entity_id}")
    assert entity_id is not None
    assert isinstance(entity_id, str)
    
    # Test historical metrics
    if entity_id:
        metrics = mock_client.get_historical_metrics(entity_id, 7)
        print(f"✅ Historical metrics: {len(metrics)} metric types retrieved")
        assert len(metrics) > 0
        assert 'builtin:service.cpu.time' in metrics
        
        # Test trend analysis
        trends = mock_client.get_trend_analysis(entity_id, 7)
        print(f"✅ Trend analysis: {trends['traffic_pattern']} pattern detected")
        print(f"   📈 CPU trend: {trends['cpu_trend']}")
        print(f"   📊 Request trend: {trends['request_rate_trend']}")
        assert 'traffic_pattern' in trends
        assert 'cpu_trend' in trends
        assert 'request_rate_trend' in trends
    
    # Test different app scenarios
    print("\n🧪 Testing different app scenarios:")
    
    # New app (no data)
    availability, details = mock_client.check_data_availability("new-app", "production")
    print(f"✅ New app data availability: {availability}")
    assert availability == 'no_historical_data'
    
    # Partial data app
    availability, details = mock_client.check_data_availability("partial-app", "production")
    print(f"✅ Partial data app availability: {availability}")
    assert availability == 'partial_data'
    if details:
        print(f"   📊 {details['days_available']} days available")
        assert details['days_available'] == 3
    
    # Peak traffic app
    peak_entity = mock_client.discover_entity("peak-service", "production")
    if peak_entity:
        peak_trends = mock_client.get_trend_analysis(peak_entity, 7)
        print(f"✅ Peak service traffic pattern: {peak_trends['traffic_pattern']}")
        assert peak_trends['traffic_pattern'] == 'peak_hours'
    
    print("\n🎉 All MCP client integration tests passed!")

if __name__ == "__main__":
    success = test_mcp_client_integration()
    sys.exit(0 if success else 1) 