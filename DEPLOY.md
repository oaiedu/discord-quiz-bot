# Deployment Guide para Discord Quiz Bot en Google Cloud Run

## Prerrequisitos

1. **Google Cloud CLI instalado**: 
   ```bash
   # macOS
   brew install google-cloud-sdk
   
   # O descarga desde: https://cloud.google.com/sdk/docs/install
   ```

2. **Autenticación en Google Cloud**:
   ```bash
   gcloud auth login
   gcloud config set project TU-PROJECT-ID
   ```

3. **Docker instalado** (opcional, Cloud Build lo maneja):
   ```bash
   # macOS
   brew install docker
   ```

## Configuración

1. **Copiar archivo de variables de entorno**:
   ```bash
   cp .env.deploy.example .env.deploy
   ```

2. **Editar `.env.deploy`** con tus valores reales:
   - `GOOGLE_CLOUD_PROJECT`: Tu ID de proyecto de Google Cloud
   - `DISCORD_TOKEN`: Token de tu bot de Discord
   - `OPENROUTER_API_KEY`: API key de OpenRouter.ai para generar preguntas
   - `GCS_BUCKET_NAME`: Nombre del bucket de Google Cloud Storage

3. **Configurar Firebase en Secret Manager**:
   - Descarga firebase_config.json desde Firebase Console > Project Settings > Service Accounts > Generate new private key
   - Súbelo a Secret Manager:
     ```bash
     gcloud secrets create firebase-config --data-file=firebase_config.json --project=TU-PROJECT-ID
     ```
   - El script descargará automáticamente este archivo durante el deploy

4. **Cargar variables de entorno**:
   ```bash
   source .env.deploy
   ```

## Deploy

1. **Hacer el script ejecutable**:
   ```bash
   chmod +x deploy.sh
   ```

2. **Ejecutar el deploy**:
   ```bash
   ./deploy.sh
   ```

## Comandos útiles post-deploy

### Gestión de Secret Manager:
```bash
# Ver todos los secretos
gcloud secrets list --project=TU-PROJECT-ID

# Ver versiones del secreto firebase-config
gcloud secrets versions list firebase-config --project=TU-PROJECT-ID

# Actualizar firebase-config
gcloud secrets versions add firebase-config --data-file=nuevo_firebase_config.json --project=TU-PROJECT-ID

# Eliminar un secreto
gcloud secrets delete firebase-config --project=TU-PROJECT-ID
```

### Ver logs en tiempo real:
```bash
gcloud logging tail "resource.type=cloud_run_revision AND resource.labels.service_name=discord-quiz-bot" --project=TU-PROJECT-ID
```

### Ver servicios de Cloud Run:
```bash
gcloud run services list --project=TU-PROJECT-ID
```

### Actualizar variables de entorno:
```bash
gcloud run services update discord-quiz-bot \
  --set-env-vars NUEVA_VAR=valor \
  --region=us-central1 \
  --project=TU-PROJECT-ID
```

### Escalar el servicio:
```bash
gcloud run services update discord-quiz-bot \
  --min-instances=0 \
  --max-instances=5 \
  --region=us-central1 \
  --project=TU-PROJECT-ID
```

### Eliminar el servicio:
```bash
gcloud run services delete discord-quiz-bot \
  --region=us-central1 \
  --project=TU-PROJECT-ID
```

## Troubleshooting

### Error de autenticación:
```bash
gcloud auth login
gcloud auth application-default login
```

### Error de permisos:
Asegúrate de tener los roles necesarios:
- Cloud Run Admin
- Cloud Build Editor
- Storage Admin (para Container Registry)

### Bot no responde:
1. Verifica los logs
2. Confirma que el token de Discord sea correcto
3. Verifica que el bot tenga los permisos necesarios en Discord

### Timeout en el deploy:
Si el bot tarda mucho en iniciar, aumenta el timeout:
```bash
--timeout 3600
```

## Costos estimados

Cloud Run es pay-per-use:
- **CPU**: ~$0.00002400 por vCPU-segundo
- **Memoria**: ~$0.00000250 por GiB-segundo  
- **Requests**: Primeros 2M gratis, luego $0.40 por millón

Para un bot pequeño/mediano: ~$5-15/mes
