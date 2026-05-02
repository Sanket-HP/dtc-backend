import firebase_admin
from firebase_admin import credentials, firestore, storage, auth

cred = credentials.Certificate("backend/firebase_key.json")

firebase_admin.initialize_app(cred, {
    "storageBucket": "datatrustcoin.appspot.com"
})

db = firestore.client()
bucket = storage.bucket()