#!/bin/bash
# DEV Environment Deployment Script for SRE Agent

set -e

# Source common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../../shared/common-functions.sh"

# Configuration
ENVIRONMENT="dev"
REGION=${AWS_DEFAULT_REGION:-us-east-1}
IMAGE_TAG=${IMAGE_TAG:-v1.0.0}

# Load environment-specific variables
if [ -f "$SCRIPT_DIR/environment-variables.env" ]; then
    source "$SCRIPT_DIR/environment-variables.env"
fi

echo -e "${GREEN}🚀 SRE Agent DEV Environment Deployment${NC}"
echo "=========================================="

# Validate environment
validate_environment $ENVIRONMENT

# Check prerequisites
check_prerequisites

# Get AWS account ID for this environment
ACCOUNT_ID=$(get_aws_account_id $ENVIRONMENT)
echo -e "${BLUE}📋 AWS Account ID for $ENVIRONMENT: ${ACCOUNT_ID}${NC}"

# Step 1: Build and push Docker images
build_and_push_images $ENVIRONMENT $REGION $ACCOUNT_ID $IMAGE_TAG

# Step 2: Create AppConfig resources
APP_CONFIG_IDS=$(create_appconfig_resources $ENVIRONMENT $REGION)

# Step 3: Deploy SAM stack
deploy_sam_stack $ENVIRONMENT $REGION $ACCOUNT_ID $IMAGE_TAG "$APP_CONFIG_IDS"

# Step 4: Get deployment outputs
OUTPUTS=$(get_deployment_outputs $ENVIRONMENT $REGION)
eval $OUTPUTS

# Step 5: Test deployment
test_deployment $ENVIRONMENT $API_URL

# Step 6: Display summary
display_deployment_summary $ENVIRONMENT $REGION $API_URL $ACCOUNT_ID

echo ""
echo -e "${BLUE}🔧 DEV Environment Configuration:${NC}"
echo "Lambda Memory: 512MB"
echo "Lambda Timeout: 15s"
echo "LLM Server: 256 CPU units, 512MB memory"
echo "MCP Server: 256 CPU units, 512MB memory"
echo "Min Replicas: 1, Max Replicas: 2"
echo ""
echo -e "${YELLOW}⚠️  Remember to configure external service credentials for DEV environment${NC}" 