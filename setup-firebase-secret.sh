#!/bin/bash

# Script for configuring firebase_config.json in Secret Manager
set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🔐 Configuring firebase_config.json in Secret Manager...${NC}"

# Variables
PROJECT_ID=${GOOGLE_CLOUD_PROJECT}
SECRET_NAME="firebase-config"

if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}❌ GOOGLE_CLOUD_PROJECT is not configured${NC}"
    echo "Run: export GOOGLE_CLOUD_PROJECT=your-project-id"
    exit 1
fi

# Verify that firebase_config.json exists locally
if [ ! -f "firebase_config.json" ]; then
    echo -e "${RED}❌ firebase_config.json not found in current directory${NC}"
    echo -e "${YELLOW}💡 Download it from Firebase Console:${NC}"
    echo "1. Go to Firebase Console > Project Settings > Service Accounts"
    echo "2. Click 'Generate new private key'"
    echo "3. Save the file as firebase_config.json in this directory"
    exit 1
fi

echo -e "${GREEN}✅ firebase_config.json found${NC}"

# Enable Secret Manager API
echo -e "${YELLOW}🔧 Enabling Secret Manager API...${NC}"
gcloud services enable secretmanager.googleapis.com --project=${PROJECT_ID}

# Verify if the secret already exists
if gcloud secrets describe ${SECRET_NAME} --project=${PROJECT_ID} >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️ Secret '${SECRET_NAME}' already exists. Do you want to update it? (y/N)${NC}"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        echo -e "${YELLOW}📝 Adding new version...${NC}"
        gcloud secrets versions add ${SECRET_NAME} --data-file=firebase_config.json --project=${PROJECT_ID}
        echo -e "${GREEN}✅ Secret updated successfully${NC}"
    else
        echo -e "${BLUE}ℹ️ No changes made${NC}"
    fi
else
    echo -e "${YELLOW}📝 Creating new secret...${NC}"
    gcloud secrets create ${SECRET_NAME} --data-file=firebase_config.json --project=${PROJECT_ID}
    echo -e "${GREEN}✅ Secret created successfully${NC}"
fi

# Verify that the secret can be accessed
echo -e "${YELLOW}🔍 Verifying secret access...${NC}"
if gcloud secrets versions access latest --secret=${SECRET_NAME} --project=${PROJECT_ID} >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Secret is accessible${NC}"
else
    echo -e "${RED}❌ Error accessing secret${NC}"
    exit 1
fi

# Display secret information
echo -e "${BLUE}📋 Secret information:${NC}"
gcloud secrets describe ${SECRET_NAME} --project=${PROJECT_ID}

echo -e "${GREEN}🎉 Configuration completed!${NC}"
echo -e "${BLUE}💡 You can now run ./deploy.sh for deployment${NC}"
