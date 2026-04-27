from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from jose import JWTError, jwt
from dotenv import load_dotenv
from sqlalchemy.orm import Session
import os
import requests
from PyPDF2 import PdfReader
from docx import Document
from sqlalchemy import func
# ===== DATABASE IMPORTS =====
from database import engine, SessionLocal, Base
import models

# Create tables
Base.metadata.create_all(bind=engine)

SIMILARITY_THRESHOLD = 80  # percent

# ===== LOAD ENV =====
load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")

app = FastAPI()
security = HTTPBearer()

# ===== CONFIG =====
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = "/app/uploads"

DOCUMENT_SERVICE_URL = "http://document-service:8001"


# ==========================
# DB DEPENDENCY
# ==========================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==========================
# JWT VERIFICATION
# ==========================

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        role = payload.get("role")

        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")

        return {
            "username": username,
            "role": role
        }

    except JWTError:
        raise HTTPException(status_code=401, detail="Token verification failed")


# ==========================
# TEXT EXTRACTION
# ==========================

def extract_text_from_pdf(file_path):
    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text


def extract_text_from_docx(file_path):
    doc = Document(file_path)
    return "\n".join([para.text for para in doc.paragraphs])


def extract_text(file_path):
    if file_path.endswith(".pdf"):
        return extract_text_from_pdf(file_path)
    elif file_path.endswith(".docx"):
        return extract_text_from_docx(file_path)
    elif file_path.endswith(".txt"):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    else:
        raise HTTPException(status_code=400, detail="Unsupported file format")


# ==========================
# SIMILARITY ENGINE
# ==========================

def calculate_similarity(text1, text2):
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform([text1, text2])
    similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])
    return round(float(similarity[0][0]) * 100, 2)


# ==========================
# SECURE COMPARE ENDPOINT
# ==========================

@app.get("/compare-by-id")
def compare_by_id(
    doc_id1: int,
    doc_id2: int,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):

    user_data = verify_token(credentials.credentials)
    username = user_data["username"]
    user_role = user_data["role"]

    res1 = requests.get(f"{DOCUMENT_SERVICE_URL}/documents/{doc_id1}")
    res2 = requests.get(f"{DOCUMENT_SERVICE_URL}/documents/{doc_id2}")

    if res1.status_code != 200 or res2.status_code != 200:
        raise HTTPException(status_code=404, detail="Document not found")

    doc1 = res1.json()
    doc2 = res2.json()

    if doc1["owner"] != username and user_role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to access doc_id1")

    if doc2["owner"] != username and user_role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to access doc_id2")

    path1 = os.path.join(UPLOAD_FOLDER, doc1["stored_filename"])
    path2 = os.path.join(UPLOAD_FOLDER, doc2["stored_filename"])

    if not os.path.exists(path1) or not os.path.exists(path2):
        raise HTTPException(status_code=404, detail="File not found on disk")

    text1 = extract_text(path1)
    text2 = extract_text(path2)

    similarity_score = calculate_similarity(text1, text2)

    return {
        "requested_by": username,
        "role": user_role,
        "doc_id1": doc_id1,
        "doc_id2": doc_id2,
        "similarity_percentage": similarity_score
    }


# ==========================
# PLAGIARISM SCAN ENDPOINT
# ==========================

@app.get("/scan/{doc_id}")
def scan_document(
    doc_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):

    user_data = verify_token(credentials.credentials)
    username = user_data["username"]
    user_role = user_data["role"]

    res = requests.get(f"{DOCUMENT_SERVICE_URL}/documents/{doc_id}")
    if res.status_code != 200:
        raise HTTPException(status_code=404, detail="Document not found")

    target_doc = res.json()

    if target_doc["owner"] != username and user_role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")

    target_path = os.path.join(UPLOAD_FOLDER, target_doc["stored_filename"])
    target_text = extract_text(target_path)

    all_docs_res = requests.get(f"{DOCUMENT_SERVICE_URL}/documents")
    all_docs = all_docs_res.json()

    results = []

    for doc in all_docs:

        if doc["id"] == doc_id:
            continue

        compare_path = os.path.join(UPLOAD_FOLDER, doc["stored_filename"])
        if not os.path.exists(compare_path):
            continue

        compare_text = extract_text(compare_path)
        similarity_score = calculate_similarity(target_text, compare_text)

        flag = similarity_score >= SIMILARITY_THRESHOLD

        # 🔥 SAVE TO DATABASE
        scan_record = models.ScanHistory(
            scanned_doc_id=doc_id,
            compared_doc_id=doc["id"],
            similarity_percentage=similarity_score,
            flagged=flag,
            scanned_by=username
        )

        db.add(scan_record)

        results.append({
            "doc_id": doc["id"],
            "owner": doc["owner"],
            "similarity_percentage": similarity_score,
            "flagged": flag
        })

    db.commit()

    results = sorted(results, key=lambda x: x["similarity_percentage"], reverse=True)

    return {
        "scanned_document": doc_id,
        "threshold": SIMILARITY_THRESHOLD,
        "results": results
    }


# ==========================
# SCAN HISTORY ENDPOINT
# ==========================

@app.get("/scan-history/{doc_id}")
def get_scan_history(
    doc_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):

    user_data = verify_token(credentials.credentials)

    history = db.query(models.ScanHistory).filter(
        models.ScanHistory.scanned_doc_id == doc_id
    ).all()

    return history

@app.get("/plagiarism-alerts")
def get_plagiarism_alerts(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    # 🔐 Verify user
    user_data = verify_token(credentials.credentials)
    username = user_data["username"]
    role = user_data["role"]

    if role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    # 🔎 Fetch only flagged cases
    alerts = db.query(models.ScanHistory).filter(
        models.ScanHistory.flagged == True
    ).order_by(models.ScanHistory.similarity_percentage.desc()).all()

    if not alerts:
        return {"message": "No plagiarism alerts found"}

    results = []

    for alert in alerts:
        # Get document metadata from document service
        res = requests.get(f"{DOCUMENT_SERVICE_URL}/documents/{alert.scanned_doc_id}")

        owner = None
        if res.status_code == 200:
            owner = res.json().get("owner")

        results.append({
            "scan_id": alert.id,
            "scanned_doc_id": alert.scanned_doc_id,
            "compared_doc_id": alert.compared_doc_id,
            "similarity_percentage": alert.similarity_percentage,
            "scanned_by": alert.scanned_by,
            "document_owner": owner,
            "timestamp": alert.timestamp
        })

    return {
        "total_alerts": len(results),
        "alerts": results
    }



@app.get("/stats")
def get_stats(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    # 🔐 Verify user (admin only)
    user_data = verify_token(credentials.credentials)
    role = user_data["role"]

    if role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    # 📊 Total scans
    total_scans = db.query(func.count(models.ScanHistory.id)).scalar()

    # 🚨 Total flagged cases
    total_flagged = db.query(func.count(models.ScanHistory.id)).filter(
        models.ScanHistory.flagged == True
    ).scalar()

    # 🔥 Highest similarity record
    highest_record = db.query(models.ScanHistory).order_by(
        models.ScanHistory.similarity_percentage.desc()
    ).first()

    highest_similarity_record = None
    if highest_record:
        highest_similarity_record = {
            "scan_id": highest_record.id,
            "scanned_doc_id": highest_record.scanned_doc_id,
            "compared_doc_id": highest_record.compared_doc_id,
            "similarity_percentage": highest_record.similarity_percentage,
            "scanned_by": highest_record.scanned_by,
            "timestamp": highest_record.timestamp
        }

    # 👤 Most active user (most scans performed)
    most_active = db.query(
        models.ScanHistory.scanned_by,
        func.count(models.ScanHistory.id).label("scan_count")
    ).group_by(
        models.ScanHistory.scanned_by
    ).order_by(
        func.count(models.ScanHistory.id).desc()
    ).first()

    most_active_user = None
    if most_active:
        most_active_user = {
            "username": most_active.scanned_by,
            "scan_count": most_active.scan_count
        }

    # 📂 Most flagged document
    most_flagged = db.query(
        models.ScanHistory.scanned_doc_id,
        func.count(models.ScanHistory.id).label("flag_count")
    ).filter(
        models.ScanHistory.flagged == True
    ).group_by(
        models.ScanHistory.scanned_doc_id
    ).order_by(
        func.count(models.ScanHistory.id).desc()
    ).first()

    most_flagged_document = None
    if most_flagged:
        most_flagged_document = {
            "document_id": most_flagged.scanned_doc_id,
            "flag_count": most_flagged.flag_count
        }

    return {
        "total_scans": total_scans,
        "total_flagged": total_flagged,
        "highest_similarity_record": highest_similarity_record,
        "most_active_user": most_active_user,
        "most_flagged_document": most_flagged_document
    }

@app.get("/risk-score/{username}")
def get_risk_score(
    username: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    # 🔐 Admin only
    user_data = verify_token(credentials.credentials)
    role = user_data["role"]

    if role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    # 📊 Total scans performed by user
    total_scans = db.query(func.count(models.ScanHistory.id)).filter(
        models.ScanHistory.scanned_by == username
    ).scalar()

    # 🚨 Total flagged cases
    total_flagged = db.query(func.count(models.ScanHistory.id)).filter(
        models.ScanHistory.scanned_by == username,
        models.ScanHistory.flagged == True
    ).scalar()

    if total_scans == 0:
        return {
            "username": username,
            "total_scans": 0,
            "total_flagged": 0,
            "flag_ratio_percent": 0,
            "risk_level": "No Activity"
        }

    flag_ratio = round((total_flagged / total_scans) * 100, 2)

    # 🧠 Risk classification
    if flag_ratio < 20:
        risk_level = "Low"
    elif flag_ratio <= 50:
        risk_level = "Medium"
    else:
        risk_level = "High"

    return {
        "username": username,
        "total_scans": total_scans,
        "total_flagged": total_flagged,
        "flag_ratio_percent": flag_ratio,
        "risk_level": risk_level
    }