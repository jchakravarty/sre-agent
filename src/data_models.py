from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, Union
from enum import Enum

# --- Request Models ---

class ApplicationContext(BaseModel):
    """Minimal application context for requests."""
    name: str
    namespace: str
    cluster: Optional[str] = None
    environment: Optional[str] = None

class DeploymentContext(BaseModel):
    """Optional deployment context for overrides."""
    environment: Optional[str] = None
    deployment_name: Optional[str] = None
    architecture: Optional[str] = None
    cost_optimization: Optional[str] = None
    traffic_pattern: Optional[str] = None
    expected_load: Optional[str] = None

class SuggestionRequest(BaseModel):
    """Main suggestion request model."""
    suggestion_type: str
    application: ApplicationContext
    deployment_context: Optional[DeploymentContext] = None

# --- Response Models ---

class DataAvailability(str, Enum):
    """Data availability levels."""
    FULL_HISTORICAL_DATA = "full_historical_data"
    PARTIAL_DATA = "partial_data"
    NO_HISTORICAL_DATA = "no_historical_data"

class InferenceSource(BaseModel):
    """Sources used for context inference."""
    deployment_type: str
    traffic_pattern: str
    cost_optimization: str
    environment: Optional[str] = None
    application_type: Optional[str] = None

class InferredContext(BaseModel):
    """Intelligently inferred deployment context."""
    deployment_type: str
    traffic_pattern: str
    cost_optimization: str
    environment: Optional[str] = None
    application_type: Optional[str] = None
    inference_source: InferenceSource

class CurrentResources(BaseModel):
    """Current resource configuration."""
    cpuRequest: Optional[str] = None
    memoryRequest: Optional[str] = None
    cpuLimit: Optional[str] = None
    memoryLimit: Optional[str] = None

class CurrentState(BaseModel):
    """Current application state."""
    current_replicas: Optional[int] = None
    current_cpu_utilization: Optional[int] = None
    current_memory_utilization: Optional[int] = None
    current_resources: Optional[CurrentResources] = None
    note: Optional[str] = None

class MetricsAnalysis(BaseModel):
    """Analysis of historical metrics."""
    avg_cpu_last_7d: Optional[int] = None
    peak_cpu_last_7d: Optional[int] = None
    avg_memory_last_7d: Optional[int] = None
    request_rate_trend: Optional[str] = None
    pod_restart_rate: Optional[str] = None
    mcp_query_used: Optional[str] = None
    mcp_query_result: Optional[str] = None
    fallback_strategy: Optional[str] = None

# --- Suggestion Models ---

class ResourceRequirements(BaseModel):
    cpu_limit: str = Field(..., alias='cpuLimit')
    memory_limit: str = Field(..., alias='memoryLimit')
    cpu_request: str = Field(..., alias='cpuRequest')
    memory_request: str = Field(..., alias='memoryRequest')

class HpaRequirements(BaseModel):
    min_replicas: int = Field(..., alias='minReplicas')
    max_replicas: int = Field(..., alias='maxReplicas')
    target_cpu_utilization_percentage: int = Field(..., alias='targetCPUUtilizationPercentage')
    scale_target_ref_name: str = Field(..., alias='scaleTargetRefName')
    resources: ResourceRequirements

    @field_validator('max_replicas')
    @classmethod
    def max_replicas_must_be_greater_than_min(cls, v, info):
        if info.data.get('min_replicas') is not None and v < info.data['min_replicas']:
            raise ValueError('max_replicas must be greater than or equal to min_replicas')
        return v

class KarpenterRequirements(BaseModel):
    architecture: str = Field(..., alias='kubernetes.io/arch')
    capacity_type: str = Field(..., alias='karpenter.sh/capacity-type')
    # Note: Removed instance-type field as it's not supported in current implementation

class ScalingSuggestionContent(BaseModel):
    """The actual scaling suggestion content."""
    hpa: HpaRequirements
    karpenter: KarpenterRequirements
    rationale: Optional[str] = None

class ScalingSuggestion(BaseModel):
    """Legacy model for backward compatibility."""
    hpa: HpaRequirements
    karpenter: KarpenterRequirements

# --- Enhanced Response Models ---

class SuggestionSource(str, Enum):
    """Source of the suggestion."""
    AI_POWERED = "ai_powered"
    AI_POWERED_WITH_FALLBACKS = "ai_powered_with_fallbacks"
    STATIC_FALLBACK = "static_fallback"

class EnhancedResponse(BaseModel):
    """Complete enhanced response structure."""
    suggestion_source: SuggestionSource
    data_availability: DataAvailability
    inferred_context: InferredContext
    current_state: CurrentState
    metrics_analysis: MetricsAnalysis
    suggestion: ScalingSuggestionContent

    model_config = {"use_enum_values": True}

# --- Quality Gate Models ---

class QualityGateApplication(BaseModel):
    """Application context for quality gate checks."""
    name: str
    commit_sha: Optional[str] = None
    artifact_id: Optional[str] = None

class QualityGateRequest(BaseModel):
    """Quality gate request model."""
    application: QualityGateApplication

class QualityGateResponse(BaseModel):
    """Quality gate response model."""
    status: str
    message: str
    score: Optional[int] = None
    details: Optional[Dict[str, Any]] = None
