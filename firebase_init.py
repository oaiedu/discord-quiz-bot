import firebase_admin
from firebase_admin import credentials, firestore, storage

cred = credentials.Certificate("firebase_config.json")
bucket_name = "oaiedu.firebasestorage.app"

firebase_admin.initialize_app(cred, {
    'storageBucket': bucket_name
})

db = firestore.client()

bucket = storage.bucket()

SERVER_TIMESTAMP = firebase_admin.firestore.SERVER_TIMESTAMP
