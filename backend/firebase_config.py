"""Firebase initialization for Firestore and Storage."""

import os
import firebase_admin
from firebase_admin import credentials, firestore, storage


# -------------------------------------------------
# Initialize Firebase Admin SDK
# -------------------------------------------------

if not firebase_admin._apps:

    cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    if cred_path and os.path.exists(cred_path):
        # Local development using service account JSON
        cred = credentials.Certificate(cred_path)

        firebase_admin.initialize_app(
            cred,
            {
                "storageBucket": "datatrustcoin.firebasestorage.app"
            },
        )

    else:
        # Cloud Run uses default service account
        firebase_admin.initialize_app(
            options={
                "storageBucket": "datatrustcoin.firebasestorage.app"
            }
        )


# -------------------------------------------------
# Firestore Database
# -------------------------------------------------

db = firestore.client()


# -------------------------------------------------
# Firebase Storage Bucket
# -------------------------------------------------

bucket = storage.bucket()


# -------------------------------------------------
# Helper: Upload file to Firebase Storage
# -------------------------------------------------

def upload_file(file_bytes: bytes, filename: str) -> str:
    """
    Upload file to Firebase Storage and return storage path
    """

    blob = bucket.blob(f"datasets/{filename}")

    blob.upload_from_string(file_bytes)

    # Do NOT make public (use signed URL instead)
    return blob.name