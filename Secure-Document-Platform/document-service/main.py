from fastapi import FastAPI, Depends, UploadFile, File, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
import models, schemas
from doc_auth import verify_token
import os
import shutil
import uuid
import hashlib

Base.metadata.create_all(bind=engine)

app = FastAPI()

security = HTTPBearer()

# ===== CONFIG =====
ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
UPLOAD_FOLDER = "uploads"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ===== DB DEPENDENCY =====
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ===== UPLOAD DOCUMENT =====
@app.post("/upload", response_model=schemas.DocumentResponse)
def upload_document(
    file: UploadFile = File(...),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    user_data = verify_token(credentials.credentials)
    username = user_data["username"]

    file_extension = file.filename.split(".")[-1].lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="File type not allowed")

    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 5MB)")

    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = os.path.join(UPLOAD_FOLDER, unique_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # ✅ SAFE HASH CALCULATION
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    file_hash = sha256.hexdigest()

    new_doc = models.Document(
        filename=file.filename,
        filepath=file_path,
        file_hash=file_hash,   # ✅ Added
        owner=username
    )

    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)

    return new_doc

# ===== GET MY DOCUMENTS =====
@app.get("/my-documents", response_model=list[schemas.DocumentResponse])
def get_my_documents(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    user_data = verify_token(credentials.credentials)
    username = user_data["username"]

    documents = db.query(models.Document).filter(
        models.Document.owner == username
    ).all()

    return documents


# ===== DOWNLOAD DOCUMENT =====
@app.get("/download/{doc_id}")
def download_document(
    doc_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    user_data = verify_token(credentials.credentials)
    username = user_data["username"]
    role = user_data["role"]

    document = db.query(models.Document).filter(
        models.Document.id == doc_id
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Owner or admin access
    if document.owner != username and role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")

    return FileResponse(document.filepath, filename=document.filename)


# ===== DELETE DOCUMENT =====
@app.delete("/delete/{doc_id}")
def delete_document(
    doc_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    user_data = verify_token(credentials.credentials)
    username = user_data["username"]
    role = user_data["role"]

    document = db.query(models.Document).filter(
        models.Document.id == doc_id
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Owner or admin access
    if document.owner != username and role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")

    # Delete file from storage
    if os.path.exists(document.filepath):
        os.remove(document.filepath)

    db.delete(document)
    db.commit()

    return {"message": "Document deleted successfully"}

# ===== INTERNAL: GET DOCUMENT METADATA =====
@app.get("/documents/{doc_id}")
def get_document_metadata(doc_id: int, db: Session = Depends(get_db)):

    document = db.query(models.Document).filter(
        models.Document.id == doc_id
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "id": document.id,
        "original_filename": document.filename,
        "stored_filename": os.path.basename(document.filepath),
        "file_hash": document.file_hash,
        "owner": document.owner
    }

@app.get("/documents")
def get_all_documents(db: Session = Depends(get_db)):

    documents = db.query(models.Document).all()

    return [
        {
            "id": doc.id,
            "original_filename": doc.filename,
            "stored_filename": os.path.basename(doc.filepath),
            "file_hash": doc.file_hash,
            "owner": doc.owner
        }
        for doc in documents
    ]