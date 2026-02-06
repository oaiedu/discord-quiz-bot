#!/bin/bash

# Script for deploying the Discord Quiz Bot to Google Cloud Run
set -e

# Function to clean up temporary files
cleanup() {
    echo -e "${YELLOW}🧹 Cleaning up temporary files...${NC}"
    rm -f firebase_config.json
}

# Set up trap to clean up on error
trap cleanup EXIT

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting deployment of Discord Quiz Bot to Cloud Run...${NC}"

# Configuration variables (modify as needed)
PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-"your-project-id"}
SERVICE_NAME="discord-quiz-bot"
REGION="us-central1"
IMAGE_NAME="${REGION}-docker.pkg.dev/${PROJECT_ID}/${SERVICE_NAME}/${SERVICE_NAME}"

# Verify user is authenticated
echo -e "${YELLOW}📋 Verifying authentication...${NC}"
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo -e "${RED}❌ Not authenticated. Run: gcloud auth login${NC}"
    exit 1
fi

# Verify that project is configured
if [ "$PROJECT_ID" = "your-project-id" ]; then
    echo -e "${RED}❌ Please configure your PROJECT_ID in the script or use the GOOGLE_CLOUD_PROJECT environment variable${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Authenticated as: $(gcloud auth list --filter=status:ACTIVE --format="value(account)")${NC}"
echo -e "${GREEN}✅ Project: ${PROJECT_ID}${NC}"

# Enable necessary APIs
echo -e "${YELLOW}🔧 Enabling necessary APIs...${NC}"
gcloud services enable cloudbuild.googleapis.com --project=${PROJECT_ID}
gcloud services enable run.googleapis.com --project=${PROJECT_ID}
gcloud services enable artifactregistry.googleapis.com --project=${PROJECT_ID}
gcloud services enable secretmanager.googleapis.com --project=${PROJECT_ID}

# Create Artifact Registry repository if it doesn't exist
echo -e "${YELLOW}📦 Configuring Artifact Registry...${NC}"
if ! gcloud artifacts repositories describe ${SERVICE_NAME} --location=${REGION} --project=${PROJECT_ID} >/dev/null 2>&1; then
    gcloud artifacts repositories create ${SERVICE_NAME} \
        --repository-format=docker \
        --location=${REGION} \
        --project=${PROJECT_ID}
    echo -e "${GREEN}✅ Artifact Registry repository created${NC}"
else
    echo -e "${GREEN}✅ Artifact Registry repository already exists${NC}"
fi

# Build the Docker image
echo -e "${YELLOW}🏗️  Building Docker image...${NC}"
gcloud builds submit --tag ${IMAGE_NAME} --project=${PROJECT_ID} --gcs-source-staging-dir=gs://oaiedu_cloudbuild/source .

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Error building the Docker image${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Image built successfully: ${IMAGE_NAME}${NC}"

# Verify required environment variables
echo -e "${YELLOW}📝 Verifying environment variables...${NC}"

# Required variables
if [ -z "$DISCORD_TOKEN" ]; then
    echo -e "${RED}❌ DISCORD_TOKEN is not configured. Please set this environment variable.${NC}"
    exit 1
fi

if [ -z "$OPENROUTER_API_KEY" ]; then
    echo -e "${RED}❌ OPENROUTER_API_KEY is not configured. Please set this environment variable.${NC}"
    exit 1
fi

if [ -z "$GCS_BUCKET_NAME" ]; then
    echo -e "${RED}❌ GCS_BUCKET_NAME is not configured. Please set this environment variable.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Environment variables verified${NC}"

# Download firebase_config.json from Secret Manager
echo -e "${YELLOW}🔐 Downloading firebase_config.json from Secret Manager...${NC}"
SECRET_NAME="firebase-config"

# Verify if the secret exists
if ! gcloud secrets describe ${SECRET_NAME} --project=${PROJECT_ID} >/dev/null 2>&1; then
    echo -e "${RED}❌ Secret '${SECRET_NAME}' not found in Secret Manager.${NC}"
    echo -e "${YELLOW}💡 Upload firebase_config.json to Secret Manager with:${NC}"
    echo "gcloud secrets create ${SECRET_NAME} --data-file=firebase_config.json --project=${PROJECT_ID}"
    exit 1
fi

# Download the secret
gcloud secrets versions access latest --secret=${SECRET_NAME} --project=${PROJECT_ID} > firebase_config.json

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Error downloading firebase_config.json from Secret Manager${NC}"
    exit 1
fi

echo -e "${GREEN}✅ firebase_config.json downloaded from Secret Manager${NC}"

# Deploy to Cloud Run
echo -e "${YELLOW}🚀 Deploying to Cloud Run...${NC}"
gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_NAME} \
    --platform managed \
    --region ${REGION} \
    --project ${PROJECT_ID} \
    --allow-unauthenticated \
    --port 8080 \
    --memory 512Mi \
    --cpu 1 \
    --min-instances 1 \
    --max-instances 10 \
    --set-env-vars DISCORD_TOKEN=${DISCORD_TOKEN} \
    --set-env-vars GOOGLE_CLOUD_PROJECT=${PROJECT_ID} \
    --set-env-vars OPENROUTER_API_KEY=${OPENROUTER_API_KEY} \
    --set-env-vars GCS_BUCKET_NAME=${GCS_BUCKET_NAME} \
    --timeout 3600

if [ $? -eq 0 ]; then
    echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
    
    # Get the service URL
    SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --platform managed --region ${REGION} --project ${PROJECT_ID} --format 'value(status.url)')
    echo -e "${GREEN}🌐 Service URL: ${SERVICE_URL}${NC}"
    
    # Display logs
    echo -e "${BLUE}📋 To view logs in real-time, run:${NC}"
    echo "gcloud logging tail \"resource.type=cloud_run_revision AND resource.labels.service_name=${SERVICE_NAME}\" --project=${PROJECT_ID}"
    
else
    echo -e "${RED}❌ Error in deployment${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Deployment script completed${NC}"
