import firebase_admin
from firebase_admin import credentials, firestore, storage
import os
import json
from google.cloud import secretmanager

def get_firebase_credentials():
    """Gets Firebase credentials (from Secret Manager or GCP default)."""
    
    if os.getenv("ENVIRONMENT", "local") == "local" and os.path.exists("firebase_config.json"):
        return credentials.Certificate("firebase_config.json")
    
    try:
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        if not project_id:
            raise ValueError("GOOGLE_CLOUD_PROJECT environment variable not set")
        
        client = secretmanager.SecretManagerServiceClient()
        secret_name = f"projects/{project_id}/secrets/firebase-config/versions/latest"
        
        response = client.access_secret_version(request={"name": secret_name})
        secret_data = response.payload.data.decode("UTF-8")
        cred_dict = json.loads(secret_data)
        return credentials.Certificate(cred_dict)
    
    except Exception as e:
        print(f"⚠️ Error getting Firebase config: {e}")
        return credentials.ApplicationDefault()

if not firebase_admin._apps:
    cred = get_firebase_credentials()
    bucket_name = "oaiedu.firebasestorage.app"
    firebase_admin.initialize_app(cred, {'storageBucket': bucket_name})

db = firestore.client()
bucket = storage.bucket()

SERVER_TIMESTAMP = firestore.SERVER_TIMESTAMP
Increment = firestore.Increment