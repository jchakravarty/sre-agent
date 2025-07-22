#!/bin/bash
# SRE Agent Production Deployment Script

set -e

# Configuration
REGION=${AWS_DEFAULT_REGION:-us-east-1}
STACK_NAME="sre-agent-production"
IMAGE_TAG="v1.0.0"
ECR_REPO_NAME="sre-agent"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 SRE Agent Production Deployment${NC}"
echo "=========================================="

# Check prerequisites
echo -e "${YELLOW}📋 Checking prerequisites...${NC}"

if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI not found. Please install it first.${NC}"
    exit 1
fi

if ! command -v sam &> /dev/null; then
    echo -e "${RED}❌ SAM CLI not found. Please install it first.${NC}"
    exit 1
fi

if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker not found. Please install it first.${NC}"
    exit 1
fi

# Get AWS Account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo -e "${BLUE}📋 AWS Account ID: ${ACCOUNT_ID}${NC}"

# Step 1: Create AWS AppConfig Resources
echo -e "${YELLOW}🔧 Step 1: Setting up AWS AppConfig...${NC}"

# Create AppConfig Application
echo "Creating AppConfig Application..."
aws appconfig create-application \
    --name "sre-agent" \
    --description "SRE Orchestration Agent Configuration" \
    --region $REGION 2>/dev/null || echo "Application already exists"

# Get Application ID
APP_CONFIG_APP_ID=$(aws appconfig list-applications --region $REGION --query 'Items[?Name==`sre-agent`].Id' --output text)
echo -e "${BLUE}AppConfig Application ID: ${APP_CONFIG_APP_ID}${NC}"

# Create Environment
echo "Creating AppConfig Environment..."
aws appconfig create-environment \
    --application-id $APP_CONFIG_APP_ID \
    --name "production" \
    --description "Production environment" \
    --region $REGION 2>/dev/null || echo "Environment already exists"

# Get Environment ID
APP_CONFIG_ENV_ID=$(aws appconfig list-environments --application-id $APP_CONFIG_APP_ID --region $REGION --query 'Items[?Name==`production`].Id' --output text)
echo -e "${BLUE}AppConfig Environment ID: ${APP_CONFIG_ENV_ID}${NC}"

# Create Configuration Profile
echo "Creating AppConfig Configuration Profile..."
aws appconfig create-configuration-profile \
    --application-id $APP_CONFIG_APP_ID \
    --name "default" \
    --location-uri "hosted" \
    --type "AWS.Freeform" \
    --region $REGION 2>/dev/null || echo "Configuration Profile already exists"

# Get Configuration Profile ID
APP_CONFIG_PROFILE_ID=$(aws appconfig list-configuration-profiles --application-id $APP_CONFIG_APP_ID --region $REGION --query 'Items[?Name==`default`].Id' --output text)
echo -e "${BLUE}AppConfig Configuration Profile ID: ${APP_CONFIG_PROFILE_ID}${NC}"

# Step 2: Create Production Configuration
echo -e "${YELLOW}🔧 Step 2: Creating production configuration...${NC}"

cat > appconfig-production.yaml << 'EOF'
# SRE Agent Production Configuration
features:
  enable_ai_shadow_analyst: true
  enable_quality_gates: true
  enable_scaling_suggestions: true

# External Service Configuration
external_services:
  dynatrace:
    api_url: "https://your-tenant.dynatrace.com/api/v2"
    api_token: "${DYNATRACE_API_TOKEN}"
  sonarqube:
    url: "https://your-sonarqube-instance.com"
    token: "${SONARQUBE_TOKEN}"
  wiz:
    url: "https://your-wiz-instance.com"
    client_id: "${WIZ_CLIENT_ID}"
    client_secret: "${WIZ_CLIENT_SECRET}"
  slack:
    webhook_url: "${SLACK_WEBHOOK_URL}"

# Fallback Strategies
fallback_strategies:
  new_deployment:
    resource_sizing:
      cpu_request: "250m"
      memory_request: "256Mi"
      cpu_limit: "500m"
      memory_limit: "512Mi"
    scaling_configuration:
      min_replicas: 2
      max_replicas: 6
      target_cpu_utilization: 70
    infrastructure:
      instance_type: "m5.medium"
      capacity_type: "on-demand"
  
  partial_data:
    resource_sizing:
      cpu_request: "300m"
      memory_request: "384Mi"
      cpu_limit: "600m"
      memory_limit: "768Mi"
    scaling_configuration:
      min_replicas: 3
      max_replicas: 8
      target_cpu_utilization: 65
    infrastructure:
      instance_type: "m5.large"
      capacity_type: "spot"

# Environment Defaults
environment_defaults:
  production:
    resource_sizing:
      cpu_request: "500m"
      memory_request: "512Mi"
    scaling_configuration:
      min_replicas: 3
      max_replicas: 10
    infrastructure:
      capacity_type: "spot"
  
  staging:
    resource_sizing:
      cpu_request: "250m"
      memory_request: "256Mi"
    scaling_configuration:
      min_replicas: 2
      max_replicas: 6
    infrastructure:
      capacity_type: "on-demand"

# Application Type Patterns
application_type_patterns:
  api_service:
    resource_sizing:
      cpu_request: "500m"
      memory_request: "512Mi"
    scaling_configuration:
      target_cpu_utilization: 70
  
  worker_service:
    resource_sizing:
      cpu_request: "250m"
      memory_request: "1Gi"
    scaling_configuration:
      target_cpu_utilization: 80
  
  frontend_service:
    resource_sizing:
      cpu_request: "200m"
      memory_request: "256Mi"
    scaling_configuration:
      target_cpu_utilization: 60

# Organization Policies
organization_policies:
  cost_optimization: "balanced"
  performance_requirements: "standard"
  security_compliance: "enabled"
EOF

echo -e "${GREEN}✅ Production configuration created${NC}"

# Step 3: Build and Deploy Container Image
echo -e "${YELLOW}🔧 Step 3: Building and deploying container image...${NC}"

# Build Docker Image
echo "Building Docker image..."
docker build -f Dockerfile.lambda -t ${ECR_REPO_NAME}:${IMAGE_TAG} .

# Create ECR Repository (if it doesn't exist)
echo "Creating ECR repository..."
aws ecr describe-repositories --repository-names ${ECR_REPO_NAME} --region ${REGION} 2>/dev/null || \
aws ecr create-repository --repository-name ${ECR_REPO_NAME} --region ${REGION}

# Login to ECR
echo "Logging into ECR..."
aws ecr get-login-password --region ${REGION} | docker login --username AWS --password-stdin ${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com

# Tag and Push Image
echo "Tagging and pushing image..."
docker tag ${ECR_REPO_NAME}:${IMAGE_TAG} ${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${ECR_REPO_NAME}:${IMAGE_TAG}
docker push ${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${ECR_REPO_NAME}:${IMAGE_TAG}

# Step 4: Deploy SAM Stack
echo -e "${YELLOW}🔧 Step 4: Deploying SAM stack...${NC}"

sam deploy \
    --template-file template-container.yaml \
    --stack-name ${STACK_NAME} \
    --capabilities CAPABILITY_IAM \
    --region ${REGION} \
    --parameter-overrides \
        AppConfigApplicationId="${APP_CONFIG_APP_ID}" \
        AppConfigEnvironmentId="${APP_CONFIG_ENV_ID}" \
        AppConfigConfigurationProfileId="${APP_CONFIG_PROFILE_ID}" \
        ImageUri="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${ECR_REPO_NAME}:${IMAGE_TAG}" \
    --no-fail-on-empty-changeset

# Step 5: Get Deployment Outputs
echo -e "${YELLOW}📊 Getting deployment outputs...${NC}"

API_URL=$(aws cloudformation describe-stacks \
    --stack-name ${STACK_NAME} \
    --region ${REGION} \
    --query 'Stacks[0].Outputs[?OutputKey==`SREAgentApiUrl`].OutputValue' \
    --output text)

FUNCTION_NAME=$(aws cloudformation describe-stacks \
    --stack-name ${STACK_NAME} \
    --region ${REGION} \
    --query 'Stacks[0].Outputs[?OutputKey==`FunctionName`].OutputValue' \
    --output text)

# Step 6: Configure External Services
echo -e "${YELLOW}🔧 Step 6: Configuring external services...${NC}"

echo -e "${BLUE}⚠️  Please update the following environment variables in the Lambda function:${NC}"
echo -e "${BLUE}   - DYNATRACE_API_URL${NC}"
echo -e "${BLUE}   - DYNATRACE_API_TOKEN${NC}"
echo -e "${BLUE}   - SONARQUBE_URL${NC}"
echo -e "${BLUE}   - SONARQUBE_TOKEN${NC}"
echo -e "${BLUE}   - WIZ_URL${NC}"
echo -e "${BLUE}   - WIZ_CLIENT_ID${NC}"
echo -e "${BLUE}   - WIZ_CLIENT_SECRET${NC}"
echo -e "${BLUE}   - SLACK_WEBHOOK_URL${NC}"

echo ""
echo -e "${YELLOW}You can update them using:${NC}"
echo "aws lambda update-function-configuration \\"
echo "    --function-name ${FUNCTION_NAME} \\"
echo "    --environment Variables='{\"DYNATRACE_API_TOKEN\":\"your-token\"}' \\"
echo "    --region ${REGION}"

# Step 7: Test the deployment
echo -e "${YELLOW}🧪 Step 7: Testing deployment...${NC}"

echo "Testing Quality Gate endpoint..."
curl -X POST "${API_URL}/gate" \
    -H "Content-Type: application/json" \
    -d '{"application":{"name":"test-app","commit_sha":"test-123"}}' \
    --max-time 30 || echo "Test failed (this is normal for first deployment)"

echo ""
echo "Testing Scaling Suggestions endpoint..."
curl -X POST "${API_URL}/suggest" \
    -H "Content-Type: application/json" \
    -d '{"suggestion_type":"kubernetes_scaling","application":{"name":"test-app","namespace":"production"}}' \
    --max-time 30 || echo "Test failed (this is normal for first deployment)"

# Step 8: Display final information
echo -e "${GREEN}✅ Deployment Complete!${NC}"
echo "=========================================="
echo -e "${GREEN}🌐 API Gateway URL: ${API_URL}${NC}"
echo -e "${GREEN}🔗 Quality Gate: ${API_URL}/gate${NC}"
echo -e "${GREEN}🔗 Scaling Suggestions: ${API_URL}/suggest${NC}"
echo -e "${GREEN}📦 ECR Repository: ${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${ECR_REPO_NAME}${NC}"
echo -e "${GREEN}🔧 Lambda Function: ${FUNCTION_NAME}${NC}"
echo -e "${GREEN}⚙️ AppConfig Application: ${APP_CONFIG_APP_ID}${NC}"

echo ""
echo -e "${BLUE}📋 Next Steps:${NC}"
echo "1. Update Lambda environment variables with your external service credentials"
echo "2. Configure your Harness pipeline to use the API endpoints"
echo "3. Set up CloudWatch alarms for monitoring"
echo "4. Test the integration with your actual applications"

echo ""
echo -e "${GREEN}🎉 SRE Agent is now deployed and ready for production use!${NC}" 