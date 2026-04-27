from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse
from jose import jwt, JWTError
from dotenv import load_dotenv
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch
import requests
import os
from datetime import datetime

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")

DOCUMENT_SERVICE_URL = os.getenv("DOCUMENT_SERVICE_URL")
VERIFICATION_SERVICE_URL = os.getenv("VERIFICATION_SERVICE_URL")
SIMILARITY_SERVICE_URL = os.getenv("SIMILARITY_SERVICE_URL")

app = FastAPI()
security = HTTPBearer()


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


# ==========================
# REPORT ENDPOINT
# ==========================

@app.get("/report/{doc_id}")
def generate_report(
    doc_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):

    user = verify_token(credentials.credentials)

    # 1️⃣ Get Document Metadata
    doc_res = requests.get(f"{DOCUMENT_SERVICE_URL}/documents/{doc_id}")
    if doc_res.status_code != 200:
        raise HTTPException(status_code=404, detail="Document not found")

    document = doc_res.json()

    # 2️⃣ Get Verification Result
    ver_res = requests.get(
        f"{VERIFICATION_SERVICE_URL}/verify/{doc_id}",
        headers={"Authorization": f"Bearer {credentials.credentials}"}
    )
    if ver_res.status_code != 200:
        raise HTTPException(status_code=400, detail="Verification failed")

    verification = ver_res.json()

    # 3️⃣ Get Similarity/Risk Score
    sim_res = requests.get(
        f"{SIMILARITY_SERVICE_URL}/risk-score/{document['owner']}",
        headers={"Authorization": f"Bearer {credentials.credentials}"}
    )

    risk_data = {}
    if sim_res.status_code == 200:
        risk_data = sim_res.json()

    # ==========================
    # PDF Generation
    # ==========================

    file_name = f"report_doc_{doc_id}.pdf"
    file_path = os.path.abspath(file_name)

    doc = SimpleDocTemplate(file_path)
    elements = []

    styles = getSampleStyleSheet()
    normal = styles["Normal"]

    elements.append(Paragraph("<b>Document Compliance Report</b>", styles["Title"]))
    elements.append(Spacer(1, 0.5 * inch))

    elements.append(Paragraph(f"Generated On: {datetime.utcnow()}", normal))
    elements.append(Spacer(1, 0.3 * inch))

    # Document Info
    elements.append(Paragraph("<b>Document Information</b>", styles["Heading2"]))
    elements.append(Spacer(1, 0.2 * inch))
    elements.append(Paragraph(f"Document ID: {doc_id}", normal))
    elements.append(Paragraph(f"Original Filename: {document['original_filename']}", normal))
    elements.append(Paragraph(f"Owner: {document['owner']}", normal))
    elements.append(Spacer(1, 0.4 * inch))

    # Verification Info
    elements.append(Paragraph("<b>Integrity Verification</b>", styles["Heading2"]))
    elements.append(Spacer(1, 0.2 * inch))
    elements.append(Paragraph(f"Hash Valid: {verification['hash_valid']}", normal))
    elements.append(Paragraph(f"Duplicate Detected: {verification['duplicate_detected']}", normal))
    elements.append(Paragraph(f"Integrity Status: {verification['integrity_status']}", normal))
    elements.append(Spacer(1, 0.4 * inch))

    # Risk Info
    elements.append(Paragraph("<b>Risk Assessment</b>", styles["Heading2"]))
    elements.append(Spacer(1, 0.2 * inch))

    if risk_data:
        elements.append(Paragraph(f"Total Scans: {risk_data.get('total_scans')}", normal))
        elements.append(Paragraph(f"Flag Ratio (%): {risk_data.get('flag_ratio_percent')}", normal))
        elements.append(Paragraph(f"Risk Level: {risk_data.get('risk_level')}", normal))
    else:
        elements.append(Paragraph("Risk data not available.", normal))

    doc.build(elements)

    return FileResponse(
        file_path,
        media_type="application/pdf",
        filename=file_name
    )