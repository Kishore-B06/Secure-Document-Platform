from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime
from database import Base

class VerificationLog(Base):
    __tablename__ = "verification_logs"

    id = Column(Integer, primary_key=True, index=True)
    doc_id = Column(Integer)
    hash_valid = Column(Boolean)
    duplicate_detected = Column(Boolean)
    verified_by = Column(String(50))
    timestamp = Column(DateTime, default=datetime.utcnow)