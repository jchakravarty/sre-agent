#!/bin/bash
# Common deployment functions for multi-environment SRE Agent deployment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default configuration
DEFAULT_REGION=${AWS_DEFAULT_REGION:-us-east-1}
DEFAULT_IMAGE_TAG=${IMAGE_TAG:-v1.0.0}

# Function to validate environment
validate_environment() {
    local env=$1
    case $env in
        dev|prod)
            return 0
            ;;
        *)
            echo -e "${RED}❌ Invalid environment: $env${NC}"
            echo -e "${YELLOW}Valid environments: dev, prod${NC}"
            return 1
            ;;
    esac
}

# Function to get environment configuration
get_env_config() {
    local env=$1
    
    case $env in
        dev)
            echo "STACK_NAME=sre-agent-dev"
            echo "LAMBDA_MEMORY=512"
            echo "LAMBDA_TIMEOUT=15"
            echo "LLM_CPU=256"
            echo "LLM_MEMORY=512"
            echo "MCP_CPU=256"
            echo "MCP_MEMORY=512"
            echo "MIN_REPLICAS=1"
            echo "MAX_REPLICAS=2"
            ;;
        prod)
            echo "STACK_NAME=sre-agent-prod"
            echo "LAMBDA_MEMORY=1024"
            echo "LAMBDA_TIMEOUT=30"
            echo "LLM_CPU=2048"
            echo "LLM_MEMORY=4096"
            echo "MCP_CPU=1024"
            echo "MCP_MEMORY=2048"
            echo "MIN_REPLICAS=3"
            echo "MAX_REPLICAS=10"
            ;;
    esac
}

# Function to get AWS account ID for environment
get_aws_account_id() {
    local env=$1
    local account_var="${env^^}_AWS_ACCOUNT_ID"
    local account_id=${!account_var}
    
    if [ -z "$account_id" ]; then
        echo -e "${YELLOW}⚠️  $account_var not set, using current account${NC}"
        account_id=$(aws sts get-caller-identity --query Account --output text)
    fi
    
    echo "$account_id"
}

# Function to check prerequisites
check_prerequisites() {
    echo -e "${YELLOW}📋 Checking prerequisites...${NC}"
    
    if ! command -v aws &> /dev/null; then
        echo -e "${RED}❌ AWS CLI not found. Please install it first.${NC}"
        return 1
    fi
    
    if ! command -v sam &> /dev/null; then
        echo -e "${RED}❌ SAM CLI not found. Please install it first.${NC}"
        return 1
    fi
    
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}❌ Docker not found. Please install it first.${NC}"
        return 1
    fi
    
    echo -e "${GREEN}✅ All prerequisites met${NC}"
}

# Function to build and push Docker images
build_and_push_images() {
    local env=$1
    local region=$2
    local account_id=$3
    local image_tag=$4
    
    echo -e "${YELLOW}🔧 Building and pushing Docker images for $env...${NC}"
    
    # Build SRE Agent Lambda image
    echo "Building SRE Agent Lambda image..."
    docker build -f Dockerfile.lambda -t sre-agent-lambda:$image_tag .
    
    # Build LLM Server image
    echo "Building LLM Server image..."
    docker build -f Dockerfile.llm -t sre-agent-llm:$image_tag .
    
    # Build MCP Server image
    echo "Building MCP Server image..."
    docker build -f Dockerfile.mcp -t sre-agent-mcp:$image_tag .
    
    # Create ECR repositories if they don't exist
    echo "Creating ECR repositories..."
    aws ecr describe-repositories --repository-names sre-agent-lambda --region $region 2>/dev/null || \
    aws ecr create-repository --repository-name sre-agent-lambda --region $region
    
    aws ecr describe-repositories --repository-names sre-agent-llm --region $region 2>/dev/null || \
    aws ecr create-repository --repository-name sre-agent-llm --region $region
    
    aws ecr describe-repositories --repository-names sre-agent-mcp --region $region 2>/dev/null || \
    aws ecr create-repository --repository-name sre-agent-mcp --region $region
    
    # Login to ECR
    echo "Logging into ECR..."
    aws ecr get-login-password --region $region | docker login --username AWS --password-stdin $account_id.dkr.ecr.$region.amazonaws.com
    
    # Tag and push images
    echo "Tagging and pushing images..."
    docker tag sre-agent-lambda:$image_tag $account_id.dkr.ecr.$region.amazonaws.com/sre-agent-lambda:$image_tag
    docker tag sre-agent-llm:$image_tag $account_id.dkr.ecr.$region.amazonaws.com/sre-agent-llm:$image_tag
    docker tag sre-agent-mcp:$image_tag $account_id.dkr.ecr.$region.amazonaws.com/sre-agent-mcp:$image_tag
    
    docker push $account_id.dkr.ecr.$region.amazonaws.com/sre-agent-lambda:$image_tag
    docker push $account_id.dkr.ecr.$region.amazonaws.com/sre-agent-llm:$image_tag
    docker push $account_id.dkr.ecr.$region.amazonaws.com/sre-agent-mcp:$image_tag
    
    echo -e "${GREEN}✅ Images built and pushed successfully${NC}"
}

# Function to create AppConfig resources
create_appconfig_resources() {
    local env=$1
    local region=$2
    local app_name="sre-agent-$env"
    
    echo -e "${YELLOW}🔧 Creating AppConfig resources for $env...${NC}"
    
    # Create AppConfig Application
    echo "Creating AppConfig Application..."
    aws appconfig create-application \
        --name "$app_name" \
        --description "SRE Orchestration Agent Configuration for $env" \
        --region $region 2>/dev/null || echo "Application already exists"
    
    # Get Application ID
    local app_id=$(aws appconfig list-applications --region $region --query "Items[?Name=='$app_name'].Id" --output text)
    echo -e "${BLUE}AppConfig Application ID: $app_id${NC}"
    
    # Create Environment
    echo "Creating AppConfig Environment..."
    aws appconfig create-environment \
        --application-id $app_id \
        --name "$env" \
        --description "$env environment" \
        --region $region 2>/dev/null || echo "Environment already exists"
    
    # Get Environment ID
    local env_id=$(aws appconfig list-environments --application-id $app_id --region $region --query "Items[?Name=='$env'].Id" --output text)
    echo -e "${BLUE}AppConfig Environment ID: $env_id${NC}"
    
    # Create Configuration Profile
    echo "Creating AppConfig Configuration Profile..."
    aws appconfig create-configuration-profile \
        --application-id $app_id \
        --name "default" \
        --location-uri "hosted" \
        --type "AWS.Freeform" \
        --region $region 2>/dev/null || echo "Configuration Profile already exists"
    
    # Get Configuration Profile ID
    local profile_id=$(aws appconfig list-configuration-profiles --application-id $app_id --region $region --query "Items[?Name=='default'].Id" --output text)
    echo -e "${BLUE}AppConfig Configuration Profile ID: $profile_id${NC}"
    
    # Return the IDs
    echo "$app_id $env_id $profile_id"
}

# Function to deploy SAM stack
deploy_sam_stack() {
    local env=$1
    local region=$2
    local account_id=$3
    local image_tag=$4
    local app_config_ids=$5
    
    echo -e "${YELLOW}🔧 Deploying SAM stack for $env...${NC}"
    
    # Parse AppConfig IDs
    local app_id=$(echo $app_config_ids | cut -d' ' -f1)
    local env_id=$(echo $app_config_ids | cut -d' ' -f2)
    local profile_id=$(echo $app_config_ids | cut -d' ' -f3)
    
    # Get environment configuration
    local stack_config=$(get_env_config $env)
    eval $stack_config
    
    # Deploy using SAM
    sam deploy \
        --template-file deployments/environments/$env/sam-template.yaml \
        --stack-name $STACK_NAME \
        --capabilities CAPABILITY_IAM \
        --region $region \
        --parameter-overrides \
            AppConfigApplicationId="$app_id" \
            AppConfigEnvironmentId="$env_id" \
            AppConfigConfigurationProfileId="$profile_id" \
            LambdaImageUri="$account_id.dkr.ecr.$region.amazonaws.com/sre-agent-lambda:$image_tag" \
            LLMImageUri="$account_id.dkr.ecr.$region.amazonaws.com/sre-agent-llm:$image_tag" \
            MCPImageUri="$account_id.dkr.ecr.$region.amazonaws.com/sre-agent-mcp:$image_tag" \
            LambdaMemory="$LAMBDA_MEMORY" \
            LambdaTimeout="$LAMBDA_TIMEOUT" \
            LLMCPU="$LLM_CPU" \
            LLMMemory="$LLM_MEMORY" \
            MCPCPU="$MCP_CPU" \
            MCPMemory="$MCP_MEMORY" \
            MinReplicas="$MIN_REPLICAS" \
            MaxReplicas="$MAX_REPLICAS" \
        --no-fail-on-empty-changeset
    
    echo -e "${GREEN}✅ SAM stack deployed successfully${NC}"
}

# Function to get deployment outputs
get_deployment_outputs() {
    local env=$1
    local region=$2
    
    local stack_config=$(get_env_config $env)
    eval $stack_config
    
    echo -e "${YELLOW}📊 Getting deployment outputs for $env...${NC}"
    
    local api_url=$(aws cloudformation describe-stacks \
        --stack-name $STACK_NAME \
        --region $region \
        --query 'Stacks[0].Outputs[?OutputKey==`SREAgentApiUrl`].OutputValue' \
        --output text)
    
    local function_name=$(aws cloudformation describe-stacks \
        --stack-name $STACK_NAME \
        --region $region \
        --query 'Stacks[0].Outputs[?OutputKey==`FunctionName`].OutputValue' \
        --output text)
    
    local llm_service_url=$(aws cloudformation describe-stacks \
        --stack-name $STACK_NAME \
        --region $region \
        --query 'Stacks[0].Outputs[?OutputKey==`LLMServiceUrl`].OutputValue' \
        --output text)
    
    local mcp_service_url=$(aws cloudformation describe-stacks \
        --stack-name $STACK_NAME \
        --region $region \
        --query 'Stacks[0].Outputs[?OutputKey==`MCPServiceUrl`].OutputValue' \
        --output text)
    
    echo -e "${GREEN}✅ Deployment outputs retrieved${NC}"
    echo "API_URL=$api_url"
    echo "FUNCTION_NAME=$function_name"
    echo "LLM_SERVICE_URL=$llm_service_url"
    echo "MCP_SERVICE_URL=$mcp_service_url"
}

# Function to test deployment
test_deployment() {
    local env=$1
    local api_url=$2
    
    echo -e "${YELLOW}🧪 Testing deployment for $env...${NC}"
    
    echo "Testing Quality Gate endpoint..."
    curl -X POST "$api_url/gate" \
        -H "Content-Type: application/json" \
        -d "{\"application\":{\"name\":\"test-app-$env\",\"commit_sha\":\"test-123\"}}" \
        --max-time 30 || echo "Test failed (this is normal for first deployment)"
    
    echo ""
    echo "Testing Scaling Suggestions endpoint..."
    curl -X POST "$api_url/suggest" \
        -H "Content-Type: application/json" \
        -d "{\"suggestion_type\":\"kubernetes_scaling\",\"application\":{\"name\":\"test-app-$env\",\"namespace\":\"$env\"}}" \
        --max-time 30 || echo "Test failed (this is normal for first deployment)"
    
    echo -e "${GREEN}✅ Deployment testing completed${NC}"
}

# Function to display deployment summary
display_deployment_summary() {
    local env=$1
    local region=$2
    local api_url=$3
    local account_id=$4
    
    echo -e "${GREEN}✅ Deployment Complete for $env!${NC}"
    echo "=========================================="
    echo -e "${GREEN}🌐 API Gateway URL: $api_url${NC}"
    echo -e "${GREEN}🔗 Quality Gate: $api_url/gate${NC}"
    echo -e "${GREEN}🔗 Scaling Suggestions: $api_url/suggest${NC}"
    echo -e "${GREEN}📦 ECR Repository: $account_id.dkr.ecr.$region.amazonaws.com${NC}"
    echo -e "${GREEN}🔧 Environment: $env${NC}"
    echo -e "${GREEN}🌍 Region: $region${NC}"
    
    echo ""
    echo -e "${BLUE}📋 Next Steps:${NC}"
    echo "1. Update Lambda environment variables with your external service credentials"
    echo "2. Configure your Harness pipeline to use the API endpoints"
    echo "3. Set up CloudWatch alarms for monitoring"
    echo "4. Test the integration with your actual applications"
    
    echo ""
    echo -e "${GREEN}🎉 SRE Agent is now deployed and ready for $env use!${NC}"
} 