from sqlalchemy import Column, Integer, String, Text, DateTime
from database.db import Base
from datetime import datetime


class ScanHistory(Base):
    __tablename__ = "scan_history"

    id = Column(Integer, primary_key=True, index=True)
    analysis_type = Column(String(50))
    crop_name = Column(String(200), nullable=True)
    disease_name = Column(String(200), nullable=True)
    severity = Column(String(50), nullable=True)
    result_summary = Column(String(500), nullable=True)
    full_result = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
