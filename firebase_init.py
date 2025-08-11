import firebase_admin
from firebase_admin import credentials, firestore, storage
import os
import json
from google.cloud import secretmanager

def get_firebase_config():
    """Obtiene la configuración de Firebase desde Secret Manager o archivo local"""
    
    # Si estamos en desarrollo local y existe el archivo, usarlo
    if os.path.exists("firebase_config.json"):
        return "firebase_config.json"
    
    # Si estamos en producción, descargar desde Secret Manager
    try:
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        if not project_id:
            raise ValueError("GOOGLE_CLOUD_PROJECT environment variable not set")
        
        client = secretmanager.SecretManagerServiceClient()
        secret_name = f"projects/{project_id}/secrets/firebase-config/versions/latest"
        
        response = client.access_secret_version(request={"name": secret_name})
        secret_data = response.payload.data.decode("UTF-8")
        
        # Guardar temporalmente el archivo
        with open("firebase_config.json", "w") as f:
            f.write(secret_data)
        
        return "firebase_config.json"
        
    except Exception as e:
        print(f"Error getting Firebase config from Secret Manager: {e}")
        # Fallback: intentar usar credenciales por defecto de Google Cloud
        return None

# Obtener credenciales de Firebase
config_path = get_firebase_config()

if config_path:
    cred = credentials.Certificate(config_path)
else:
    # Usar credenciales por defecto de Google Cloud
    cred = credentials.ApplicationDefault()

bucket_name = "oaiedu.firebasestorage.app"

firebase_admin.initialize_app(cred, {
    'storageBucket': bucket_name
})

db = firestore.client()
bucket = storage.bucket()

SERVER_TIMESTAMP = firestore.SERVER_TIMESTAMP
Increment = firestore.Increment