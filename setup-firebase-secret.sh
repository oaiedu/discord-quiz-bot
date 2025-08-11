#!/bin/bash

# Script para configurar firebase_config.json en Secret Manager
set -e

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🔐 Configurando firebase_config.json en Secret Manager...${NC}"

# Variables
PROJECT_ID=${GOOGLE_CLOUD_PROJECT}
SECRET_NAME="firebase-config"

if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}❌ GOOGLE_CLOUD_PROJECT no está configurado${NC}"
    echo "Ejecuta: export GOOGLE_CLOUD_PROJECT=tu-proyecto-id"
    exit 1
fi

# Verificar que firebase_config.json existe localmente
if [ ! -f "firebase_config.json" ]; then
    echo -e "${RED}❌ firebase_config.json no encontrado en el directorio actual${NC}"
    echo -e "${YELLOW}💡 Descárgalo desde Firebase Console:${NC}"
    echo "1. Ve a Firebase Console > Project Settings > Service Accounts"
    echo "2. Click en 'Generate new private key'"
    echo "3. Guarda el archivo como firebase_config.json en este directorio"
    exit 1
fi

echo -e "${GREEN}✅ firebase_config.json encontrado${NC}"

# Habilitar Secret Manager API
echo -e "${YELLOW}🔧 Habilitando Secret Manager API...${NC}"
gcloud services enable secretmanager.googleapis.com --project=${PROJECT_ID}

# Verificar si el secreto ya existe
if gcloud secrets describe ${SECRET_NAME} --project=${PROJECT_ID} >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️ Secret '${SECRET_NAME}' ya existe. ¿Quieres actualizarlo? (y/N)${NC}"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        echo -e "${YELLOW}📝 Añadiendo nueva versión...${NC}"
        gcloud secrets versions add ${SECRET_NAME} --data-file=firebase_config.json --project=${PROJECT_ID}
        echo -e "${GREEN}✅ Secret actualizado exitosamente${NC}"
    else
        echo -e "${BLUE}ℹ️ No se realizaron cambios${NC}"
    fi
else
    echo -e "${YELLOW}📝 Creando nuevo secret...${NC}"
    gcloud secrets create ${SECRET_NAME} --data-file=firebase_config.json --project=${PROJECT_ID}
    echo -e "${GREEN}✅ Secret creado exitosamente${NC}"
fi

# Verificar que se puede acceder al secreto
echo -e "${YELLOW}🔍 Verificando acceso al secret...${NC}"
if gcloud secrets versions access latest --secret=${SECRET_NAME} --project=${PROJECT_ID} >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Secret accesible correctamente${NC}"
else
    echo -e "${RED}❌ Error al acceder al secret${NC}"
    exit 1
fi

# Mostrar información del secreto
echo -e "${BLUE}📋 Información del secret:${NC}"
gcloud secrets describe ${SECRET_NAME} --project=${PROJECT_ID}

echo -e "${GREEN}🎉 Configuración completada!${NC}"
echo -e "${BLUE}💡 Ahora puedes ejecutar ./deploy.sh para hacer el deploy${NC}"
