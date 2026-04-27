from sqlalchemy import Column, Integer, String, TIMESTAMP, text
from database import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255))
    filepath = Column(String(500))
    file_hash = Column(String(64), nullable=True)
    owner = Column(String(100))
    created_at = Column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP")
    )