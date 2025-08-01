# firebase_init.py
import firebase_admin
from firebase_admin import credentials, firestore

# Inicialize o Firebase com seu arquivo de credencial
cred = credentials.Certificate("firebase_config.json")
firebase_admin.initialize_app(cred)

# Obtenha o cliente Firestore
db = firestore.client()
SERVER_TIMESTAMP = firebase_admin.firestore.SERVER_TIMESTAMP  # Exporta constante