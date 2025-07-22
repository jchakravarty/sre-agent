# Harness Integration Examples

This folder contains comprehensive examples for integrating the SRE Agent with Harness CI/CD platform.

## 📁 Files Overview

### 1. `harness-integration-example.yaml`
**Purpose**: Complete Harness Pipeline integration example
**Description**: A full-featured Harness pipeline YAML that demonstrates how to integrate SRE Agent quality gates and scaling recommendations into a CI/CD pipeline.

**Key Features**:
- Quality Gate Check stage using SRE Agent `/gate` endpoint
- Scaling Recommendations stage using SRE Agent `/suggest` endpoint
- Post-deployment Validation stage using SRE Agent `/validate` endpoint
- Dynamic Kubernetes manifest updates with SRE Agent recommendations
- Environment-specific configurations for staging and production

**Usage**: Import this YAML into your Harness project to create a complete pipeline with SRE Agent integration.

### 2. `harness-service-object-example.yaml`
**Purpose**: Harness Service Object configuration example
**Description**: A comprehensive service definition that shows how to configure a Harness service with SRE Agent integration points.

**Key Features**:
- Kubernetes service definition with multiple manifest types (K8s, Kustomize, Helm)
- SRE Agent integration variables and configuration
- Service hooks for pre/post-deployment SRE Agent calls
- Dynamic scaling parameter injection
- Configuration files for SRE Agent, monitoring, and scaling
- Example Kubernetes manifests with SRE Agent integration

**Usage**: Import this YAML to create a Harness service that automatically integrates with SRE Agent for quality gates and scaling.

### 3. `harness_integration_example.py`
**Purpose**: Python code example for Harness integration
**Description**: A Python script demonstrating how to programmatically integrate with SRE Agent from Harness pipelines.

**Key Features**:
- SRE Agent API client implementation
- Quality gate checking functions
- Scaling recommendation processing
- Error handling and fallback strategies
- Integration with Harness pipeline variables

**Usage**: Use this as a reference for implementing custom Harness pipeline steps or service hooks.

## 🚀 Integration Workflow

### Pipeline Integration Flow
1. **Quality Gate Check** → SRE Agent validates code quality, security, and performance
2. **Deploy to Staging** → Standard Kubernetes deployment
3. **Get Scaling Recommendations** → SRE Agent provides intelligent scaling suggestions
4. **Deploy to Production** → Deployment with SRE Agent recommendations applied
5. **Post-Deployment Validation** → SRE Agent validates deployment success

### Service Integration Flow
1. **Pre-deployment Hook** → Quality gate check via SRE Agent API
2. **Scaling Hook** → Get and apply scaling recommendations
3. **Deployment** → Kubernetes deployment with SRE Agent parameters
4. **Post-deployment Hook** → Validation and monitoring setup

## 📋 Prerequisites

### Required Harness Connectors
- **HTTP Connector**: For SRE Agent API calls
- **Docker Hub Connector**: For container images
- **GitHub Connector**: For manifests and configuration
- **Kubernetes Connector**: For cluster deployments
- **Secret Manager Connector**: For API keys and credentials

### Required Secrets
- `sre_agent_api_key`: API key for SRE Agent authentication
- `database_credentials`: Database connection credentials
- `external_api_key`: External service API keys

### Required Services
- Kubernetes service definition
- Environment configurations (staging, production)
- Infrastructure definitions

## 🔧 Configuration Steps

### 1. Import Examples
```bash
# Import pipeline example
harness-cli import pipeline -f harness-integration-example.yaml

# Import service example
harness-cli import service -f harness-service-object-example.yaml
```

### 2. Configure Connectors
- Set up HTTP connector for SRE Agent API
- Configure Docker Hub connector for artifacts
- Set up GitHub connector for manifests
- Configure Kubernetes connector for deployments

### 3. Set Up Secrets
- Create SRE Agent API key secret
- Configure database credentials
- Set up external API keys

### 4. Update Variables
- Set `sre_agent_url` to your API Gateway URL
- Configure `app_name` and `namespace`
- Set environment-specific variables

### 5. Create Kubernetes Manifests
- Deploy the example manifests to your Git repository
- Update paths and configurations as needed
- Ensure SRE Agent labels are applied

## 🎯 Best Practices

### 1. Environment Separation
- Use different SRE Agent configurations per environment
- Implement environment-specific quality gates
- Configure appropriate scaling thresholds

### 2. Error Handling
- Implement graceful fallbacks when SRE Agent is unavailable
- Use conditional execution based on service availability
- Log all SRE Agent interactions for debugging

### 3. Security
- Use Harness secrets for all sensitive data
- Implement proper API key rotation
- Validate SRE Agent responses before applying changes

### 4. Monitoring
- Monitor SRE Agent API response times
- Track quality gate pass/fail rates
- Monitor scaling recommendation accuracy

## 🔍 Troubleshooting

### Common Issues

1. **SRE Agent API Unavailable**
   - Check API Gateway URL configuration
   - Verify API key is valid
   - Ensure network connectivity

2. **Quality Gate Failures**
   - Review SRE Agent logs for specific failures
   - Check application metrics and thresholds
   - Verify code quality and security scan results

3. **Scaling Issues**
   - Validate Kubernetes cluster capacity
   - Check HPA configuration
   - Review SRE Agent scaling recommendations

4. **Deployment Failures**
   - Verify Kubernetes manifests are valid
   - Check resource limits and requests
   - Ensure namespace and RBAC permissions

### Debug Commands
```bash
# Test SRE Agent connectivity
curl -X GET "${SRE_AGENT_URL}/health" \
  -H "X-API-Key: ${SRE_AGENT_API_KEY}"

# Test quality gate endpoint
curl -X POST "${SRE_AGENT_URL}/gate" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${SRE_AGENT_API_KEY}" \
  -d '{"application": {"name": "test-app"}}'

# Test scaling suggestions
curl -X POST "${SRE_AGENT_URL}/suggest" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${SRE_AGENT_API_KEY}" \
  -d '{"suggestion_type": "kubernetes_scaling", "application": {"name": "test-app"}}'
```

## 📚 Additional Resources

- [SRE Agent API Documentation](../docs/API.md)
- [Harness Pipeline Documentation](https://docs.harness.io/category/pipelines)
- [Harness Service Documentation](https://docs.harness.io/category/services)
- [Kubernetes Integration Guide](https://docs.harness.io/category/kubernetes)

## 🤝 Support

For issues with these examples or SRE Agent integration:
- Check the main project README for troubleshooting
- Review Harness documentation for platform-specific issues
- Open an issue in the project repository 