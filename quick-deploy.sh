#!/bin/bash

# Quick redeployment script (after initial deployment)
set -e

# Function to clean up temporary files
cleanup() {
    echo -e "${YELLOW}🧹 Cleaning up temporary files...${NC}"
    rm -f firebase_config.json
}

# Set up trap to clean up on error
trap cleanup EXIT

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🚀 Quick redeployment of Discord Quiz Bot...${NC}"

# Variables
PROJECT_ID=${GOOGLE_CLOUD_PROJECT}
SERVICE_NAME="discord-quiz-bot"
REGION="us-central1"
IMAGE_NAME="${REGION}-docker.pkg.dev/${PROJECT_ID}/${SERVICE_NAME}/${SERVICE_NAME}"

# Verify that variables are configured
if [ -z "$PROJECT_ID" ] || [ -z "$DISCORD_TOKEN" ] || [ -z "$OPENROUTER_API_KEY" ] || [ -z "$GCS_BUCKET_NAME" ]; then
    echo -e "${YELLOW}⚠️ Loading variables from .env.deploy...${NC}"
    if [ -f ".env.deploy" ]; then
        source .env.deploy
    else
        echo "❌ .env.deploy file not found. Run the full deployment first."
        exit 1
    fi
fi

# Download firebase_config.json from Secret Manager
echo -e "${YELLOW}🔐 Downloading firebase_config.json...${NC}"
gcloud secrets versions access latest --secret=firebase-config --project=${PROJECT_ID} > firebase_config.json

# Build and deploy
echo -e "${YELLOW}🏗️ Building image...${NC}"
gcloud builds submit --tag ${IMAGE_NAME} --project=${PROJECT_ID} --gcs-source-staging-dir=gs://oaiedu_cloudbuild/source .

echo -e "${YELLOW}🚀 Updating service...${NC}"
gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_NAME} \
    --region ${REGION} \
    --project ${PROJECT_ID}

echo -e "${GREEN}✅ Redeployment completed!${NC}"
