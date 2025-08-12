#!/bin/bash

# Script rápido para redeploy (después del primer deploy)
set -e

# Función para limpiar archivos temporales
cleanup() {
    echo -e "${YELLOW}🧹 Limpiando archivos temporales...${NC}"
    rm -f firebase_config.json
}

# Configurar trap para limpiar en caso de error
trap cleanup EXIT

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🚀 Redeploy rápido del Discord Quiz Bot...${NC}"

# Variables
PROJECT_ID=${GOOGLE_CLOUD_PROJECT}
SERVICE_NAME="discord-quiz-bot"
REGION="us-central1"
IMAGE_NAME="${REGION}-docker.pkg.dev/${PROJECT_ID}/${SERVICE_NAME}/${SERVICE_NAME}"

# Verificar que las variables estén configuradas
if [ -z "$PROJECT_ID" ] || [ -z "$DISCORD_TOKEN" ] || [ -z "$OPENROUTER_API_KEY" ] || [ -z "$GCS_BUCKET_NAME" ]; then
    echo -e "${YELLOW}⚠️ Cargando variables de .env.deploy...${NC}"
    if [ -f ".env.deploy" ]; then
        source .env.deploy
    else
        echo "❌ Archivo .env.deploy no encontrado. Ejecuta el deploy completo primero."
        exit 1
    fi
fi

# Descargar firebase_config.json desde Secret Manager
echo -e "${YELLOW}🔐 Descargando firebase_config.json...${NC}"
gcloud secrets versions access latest --secret=firebase-config --project=${PROJECT_ID} > firebase_config.json

# Build y deploy
echo -e "${YELLOW}🏗️ Construyendo imagen...${NC}"
gcloud builds submit --tag ${IMAGE_NAME} --project=${PROJECT_ID} --gcs-source-staging-dir=gs://oaiedu_cloudbuild/source .

echo -e "${YELLOW}🚀 Actualizando servicio...${NC}"
gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_NAME} \
    --region ${REGION} \
    --project ${PROJECT_ID}

echo -e "${GREEN}✅ Redeploy completado!${NC}"
