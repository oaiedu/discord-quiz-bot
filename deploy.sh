#!/bin/bash

# Script para hacer deploy del Discord Quiz Bot a Google Cloud Run
set -e

# Función para limpiar archivos temporales
cleanup() {
    echo -e "${YELLOW}🧹 Limpiando archivos temporales...${NC}"
    rm -f firebase_config.json
}

# Configurar trap para limpiar en caso de error
trap cleanup EXIT

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Iniciando deploy del Discord Quiz Bot a Cloud Run...${NC}"

# Variables de configuración (modifica según tus necesidades)
PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-"tu-proyecto-id"}
SERVICE_NAME="discord-quiz-bot"
REGION="us-central1"
IMAGE_NAME="${REGION}-docker.pkg.dev/${PROJECT_ID}/${SERVICE_NAME}/${SERVICE_NAME}"

# Verificar que el usuario esté autenticado
echo -e "${YELLOW}📋 Verificando autenticación...${NC}"
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo -e "${RED}❌ No estás autenticado. Ejecuta: gcloud auth login${NC}"
    exit 1
fi

# Verificar que el proyecto esté configurado
if [ "$PROJECT_ID" = "tu-proyecto-id" ]; then
    echo -e "${RED}❌ Por favor, configura tu PROJECT_ID en el script o usa la variable de entorno GOOGLE_CLOUD_PROJECT${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Autenticado como: $(gcloud auth list --filter=status:ACTIVE --format="value(account)")${NC}"
echo -e "${GREEN}✅ Proyecto: ${PROJECT_ID}${NC}"

# Habilitar APIs necesarias
echo -e "${YELLOW}🔧 Habilitando APIs necesarias...${NC}"
gcloud services enable cloudbuild.googleapis.com --project=${PROJECT_ID}
gcloud services enable run.googleapis.com --project=${PROJECT_ID}
gcloud services enable artifactregistry.googleapis.com --project=${PROJECT_ID}
gcloud services enable secretmanager.googleapis.com --project=${PROJECT_ID}

# Crear repositorio de Artifact Registry si no existe
echo -e "${YELLOW}📦 Configurando Artifact Registry...${NC}"
if ! gcloud artifacts repositories describe ${SERVICE_NAME} --location=${REGION} --project=${PROJECT_ID} >/dev/null 2>&1; then
    gcloud artifacts repositories create ${SERVICE_NAME} \
        --repository-format=docker \
        --location=${REGION} \
        --project=${PROJECT_ID}
    echo -e "${GREEN}✅ Repositorio de Artifact Registry creado${NC}"
else
    echo -e "${GREEN}✅ Repositorio de Artifact Registry ya existe${NC}"
fi

# Construir la imagen Docker
echo -e "${YELLOW}🏗️  Construyendo imagen Docker...${NC}"
gcloud builds submit --tag ${IMAGE_NAME} --project=${PROJECT_ID} --gcs-source-staging-dir=gs://oaiedu_cloudbuild/source .

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Error al construir la imagen Docker${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Imagen construida exitosamente: ${IMAGE_NAME}${NC}"

# Verificar variables de entorno necesarias
echo -e "${YELLOW}📝 Verificando variables de entorno...${NC}"

# Variables requeridas
if [ -z "$DISCORD_TOKEN" ]; then
    echo -e "${RED}❌ DISCORD_TOKEN no está configurado. Por favor, configura esta variable de entorno.${NC}"
    exit 1
fi

if [ -z "$OPENROUTER_API_KEY" ]; then
    echo -e "${RED}❌ OPENROUTER_API_KEY no está configurado. Por favor, configura esta variable de entorno.${NC}"
    exit 1
fi

if [ -z "$GCS_BUCKET_NAME" ]; then
    echo -e "${RED}❌ GCS_BUCKET_NAME no está configurado. Por favor, configura esta variable de entorno.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Variables de entorno verificadas${NC}"

# Descargar firebase_config.json desde Secret Manager
echo -e "${YELLOW}🔐 Descargando firebase_config.json desde Secret Manager...${NC}"
SECRET_NAME="firebase-config"

# Verificar si el secreto existe
if ! gcloud secrets describe ${SECRET_NAME} --project=${PROJECT_ID} >/dev/null 2>&1; then
    echo -e "${RED}❌ Secret '${SECRET_NAME}' no encontrado en Secret Manager.${NC}"
    echo -e "${YELLOW}💡 Sube firebase_config.json a Secret Manager con:${NC}"
    echo "gcloud secrets create ${SECRET_NAME} --data-file=firebase_config.json --project=${PROJECT_ID}"
    exit 1
fi

# Descargar el secreto
gcloud secrets versions access latest --secret=${SECRET_NAME} --project=${PROJECT_ID} > firebase_config.json

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Error al descargar firebase_config.json desde Secret Manager${NC}"
    exit 1
fi

echo -e "${GREEN}✅ firebase_config.json descargado desde Secret Manager${NC}"

# Hacer deploy a Cloud Run
echo -e "${YELLOW}🚀 Haciendo deploy a Cloud Run...${NC}"
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
    echo -e "${GREEN}🎉 Deploy completado exitosamente!${NC}"
    
    # Obtener la URL del servicio
    SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --platform managed --region ${REGION} --project ${PROJECT_ID} --format 'value(status.url)')
    echo -e "${GREEN}🌐 URL del servicio: ${SERVICE_URL}${NC}"
    
    # Mostrar logs
    echo -e "${BLUE}📋 Para ver los logs en tiempo real, ejecuta:${NC}"
    echo "gcloud logging tail \"resource.type=cloud_run_revision AND resource.labels.service_name=${SERVICE_NAME}\" --project=${PROJECT_ID}"
    
else
    echo -e "${RED}❌ Error en el deploy${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Script de deploy completado${NC}"
