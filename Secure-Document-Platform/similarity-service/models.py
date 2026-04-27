from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime
from datetime import datetime
from database import Base

class ScanHistory(Base):
    __tablename__ = "scan_history"

    id = Column(Integer, primary_key=True, index=True)
    scanned_doc_id = Column(Integer)
    compared_doc_id = Column(Integer)
    similarity_percentage = Column(Float)
    flagged = Column(Boolean)
    scanned_by = Column(String(50))
    timestamp = Column(DateTime, default=datetime.utcnow)