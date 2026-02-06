# Deployment Guide for Discord Quiz Bot on Google Cloud Run

## Prerequisites

1. **Google Cloud CLI installed**: 
   ```bash
   # macOS
   brew install google-cloud-sdk
   
   # Or download from: https://cloud.google.com/sdk/docs/install
   ```

2. **Google Cloud Authentication**:
   ```bash
   gcloud auth login
   gcloud config set project YOUR-PROJECT-ID
   ```

3. **Docker installed** (optional, Cloud Build handles it):
   ```bash
   # macOS
   brew install docker
   ```

## Configuration

1. **Copy environment variables file**:
   ```bash
   cp .env.deploy.example .env.deploy
   ```

2. **Edit `.env.deploy`** with your actual values:
   - `GOOGLE_CLOUD_PROJECT`: Your Google Cloud project ID
   - `DISCORD_TOKEN`: Your Discord bot token
   - `OPENROUTER_API_KEY`: API key from OpenRouter.ai for question generation
   - `GCS_BUCKET_NAME`: Google Cloud Storage bucket name

3. **Configure Firebase in Secret Manager**:
   - Download firebase_config.json from Firebase Console > Project Settings > Service Accounts > Generate new private key
   - Upload it to Secret Manager:
     ```bash
     gcloud secrets create firebase-config --data-file=firebase_config.json --project=YOUR-PROJECT-ID
     ```
   - The script will automatically download this file during deployment

4. **Load environment variables**:
   ```bash
   source .env.deploy
   ```

## Deploy

1. **Make the script executable**:
   ```bash
   chmod +x deploy.sh
   ```

2. **Run the deployment**:
   ```bash
   ./deploy.sh
   ```

## Useful commands after deployment

### Secret Manager management:
```bash
# List all secrets
gcloud secrets list --project=YOUR-PROJECT-ID

# List versions of firebase-config secret
gcloud secrets versions list firebase-config --project=YOUR-PROJECT-ID

# Update firebase-config
gcloud secrets versions add firebase-config --data-file=new_firebase_config.json --project=YOUR-PROJECT-ID

# Delete a secret
gcloud secrets delete firebase-config --project=YOUR-PROJECT-ID
```

### View logs in real-time:
```bash
gcloud logging tail "resource.type=cloud_run_revision AND resource.labels.service_name=discord-quiz-bot" --project=YOUR-PROJECT-ID
```

### View Cloud Run services:
```bash
gcloud run services list --project=YOUR-PROJECT-ID
```

### Update environment variables:
```bash
gcloud run services update discord-quiz-bot \
  --set-env-vars NEW_VAR=value \
  --region=us-central1 \
  --project=YOUR-PROJECT-ID
```

### Scale the service:
```bash
gcloud run services update discord-quiz-bot \
  --min-instances=0 \
  --max-instances=5 \
  --region=us-central1 \
  --project=YOUR-PROJECT-ID
```

### Delete the service:
```bash
gcloud run services delete discord-quiz-bot \
  --region=us-central1 \
  --project=YOUR-PROJECT-ID
```

## Troubleshooting

### Authentication error:
```bash
gcloud auth login
gcloud auth application-default login
```

### Permission error:
Make sure you have the required roles:
- Cloud Run Admin
- Cloud Build Editor
- Storage Admin (for Container Registry)

### Bot not responding:
1. Check the logs
2. Confirm the Discord token is correct
3. Verify the bot has the necessary permissions in Discord

### Deployment timeout:
If the bot takes too long to start, increase the timeout:
```bash
--timeout 3600
```

## Estimated costs

Cloud Run is pay-per-use:
- **CPU**: ~$0.00002400 per vCPU-second
- **Memory**: ~$0.00000250 per GiB-second  
- **Requests**: First 2M free, then $0.40 per million

For a small/medium bot: ~$5-15/month
