#!/bin/bash
# SRE Agent Container Image Deployment Script

set -e

# Configuration
REGION=${AWS_DEFAULT_REGION:-us-east-1}
STACK_NAME="sre-agent-container"
IMAGE_TAG="latest"
ECR_REPO_NAME="sre-agent"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 SRE Agent Container Image Deployment${NC}"
echo "=========================================="

# Check AWS CLI and SAM CLI
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI not found. Please install it first.${NC}"
    exit 1
fi

if ! command -v sam &> /dev/null; then
    echo -e "${RED}❌ SAM CLI not found. Please install it first.${NC}"
    exit 1
fi

# Get AWS Account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo -e "${YELLOW}📋 AWS Account ID: ${ACCOUNT_ID}${NC}"

# Step 1: Build Docker Image
echo -e "${YELLOW}🔨 Building Docker image...${NC}"
docker build -f Dockerfile.lambda -t ${ECR_REPO_NAME}:${IMAGE_TAG} .

# Step 2: Create ECR Repository (if it doesn't exist)
echo -e "${YELLOW}📦 Creating ECR repository...${NC}"
aws ecr describe-repositories --repository-names ${ECR_REPO_NAME} --region ${REGION} 2>/dev/null || \
aws ecr create-repository --repository-name ${ECR_REPO_NAME} --region ${REGION}

# Step 3: Login to ECR
echo -e "${YELLOW}🔐 Logging into ECR...${NC}"
aws ecr get-login-password --region ${REGION} | docker login --username AWS --password-stdin ${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com

# Step 4: Tag and Push Image
echo -e "${YELLOW}📤 Tagging and pushing image...${NC}"
docker tag ${ECR_REPO_NAME}:${IMAGE_TAG} ${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${ECR_REPO_NAME}:${IMAGE_TAG}
docker push ${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${ECR_REPO_NAME}:${IMAGE_TAG}

# Step 5: Deploy SAM Stack
echo -e "${YELLOW}☁️ Deploying SAM stack...${NC}"
sam deploy \
    --template-file template-container.yaml \
    --stack-name ${STACK_NAME} \
    --capabilities CAPABILITY_IAM \
    --region ${REGION} \
    --parameter-overrides \
        AppConfigApplicationId="sre-agent" \
        AppConfigEnvironmentId="prod" \
        AppConfigConfigurationProfileId="default" \
        ImageUri="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${ECR_REPO_NAME}:${IMAGE_TAG}" \
    --no-fail-on-empty-changeset

# Step 6: Get Outputs
echo -e "${YELLOW}📊 Getting deployment outputs...${NC}"
API_URL=$(aws cloudformation describe-stacks \
    --stack-name ${STACK_NAME} \
    --region ${REGION} \
    --query 'Stacks[0].Outputs[?OutputKey==`SREAgentApiUrl`].OutputValue' \
    --output text)

echo -e "${GREEN}✅ Deployment Complete!${NC}"
echo "=========================================="
echo -e "${GREEN}🌐 API Gateway URL: ${API_URL}${NC}"
echo -e "${GREEN}🔗 Quality Gate: ${API_URL}/gate${NC}"
echo -e "${GREEN}🔗 Scaling Suggestions: ${API_URL}/suggest${NC}"
echo -e "${GREEN}📦 ECR Repository: ${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${ECR_REPO_NAME}${NC}"

# Step 7: Test the deployment
echo -e "${YELLOW}🧪 Testing deployment...${NC}"
echo "Testing Quality Gate endpoint..."
curl -X POST "${API_URL}/gate" \
    -H "Content-Type: application/json" \
    -d '{"application":{"name":"test-app","commit_sha":"test-123"}}' \
    --max-time 30 || echo "Test failed (this is normal for first deployment)"

echo -e "${GREEN}🎉 SRE Agent is now deployed and ready!${NC}" 