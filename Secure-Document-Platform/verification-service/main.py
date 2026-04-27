from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import func
from jose import jwt, JWTError
from dotenv import load_dotenv
import hashlib
import os
import requests

from database import engine, SessionLocal, Base
import models

Base.metadata.create_all(bind=engine)

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")

DOCUMENT_SERVICE_URL = "http://document-service:8001"

app = FastAPI()
security = HTTPBearer()


# ==========================
# DB Dependency
# ==========================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==========================
# JWT Verification
# ==========================

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return {
            "username": payload.get("sub"),
            "role": payload.get("role")
        }
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def require_admin(user):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")


# ==========================
# Hash Calculation
# ==========================

def calculate_hash(file_path):
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


# ==========================
# VERIFY ENDPOINT
# ==========================

@app.get("/verify/{doc_id}")
def verify_document(
    doc_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    user = verify_token(credentials.credentials)
    username = user["username"]

    # Fetch document metadata
    res = requests.get(f"{DOCUMENT_SERVICE_URL}/documents/{doc_id}")

    if res.status_code != 200:
        raise HTTPException(status_code=404, detail="Document not found")

    doc = res.json()

    
    stored_hash = doc.get("file_hash")

    if not stored_hash:
        raise HTTPException(
        status_code=400,
        detail="Document does not contain stored hash. Re-upload required."
    )
    stored_filename = doc["stored_filename"]

    file_path = os.path.join("/app/uploads", stored_filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    recalculated_hash = calculate_hash(file_path)

    hash_valid = recalculated_hash == stored_hash

    # Duplicate detection (same hash in other docs)
    all_docs_res = requests.get(f"{DOCUMENT_SERVICE_URL}/documents")
    all_docs = all_docs_res.json()

    duplicate_detected = False

    for d in all_docs:
        if d["id"] != doc_id and d["file_hash"] == stored_hash:
            duplicate_detected = True
            break

    # Log verification
    log = models.VerificationLog(
        doc_id=doc_id,
        hash_valid=hash_valid,
        duplicate_detected=duplicate_detected,
        verified_by=username
    )

    db.add(log)
    db.commit()

    return {
        "doc_id": doc_id,
        "hash_valid": hash_valid,
        "duplicate_detected": duplicate_detected,
        "integrity_status": (
            "Verified"
            if hash_valid and not duplicate_detected
            else "Duplicate Detected"
            if duplicate_detected
            else "Hash Mismatch"
        )
    }

@app.get("/verification-logs/{doc_id}")
def get_verification_logs(
    doc_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    user = verify_token(credentials.credentials)

    # 🔐 Admin Only
    require_admin(user)

    logs = db.query(models.VerificationLog).filter(
        models.VerificationLog.doc_id == doc_id
    ).order_by(models.VerificationLog.timestamp.desc()).all()

    if not logs:
        raise HTTPException(status_code=404, detail="No verification logs found")

    return [
        {
            "doc_id": log.doc_id,
            "hash_valid": log.hash_valid,
            "duplicate_detected": log.duplicate_detected,
            "verified_by": log.verified_by,
            "timestamp": log.timestamp
        }
        for log in logs
    ]