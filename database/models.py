from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database.db import Base
from datetime import datetime


# ─── User Model ─────────────────────────────────────────────────────────────
class User(Base):
    """Stores registered users. Role is either 'user' or 'admin'."""
    __tablename__ = "users"

    id         = Column(Integer, primary_key=True, index=True)
    name       = Column(String(100), nullable=False)
    email      = Column(String(100), unique=True, index=True, nullable=True)  # Email column for login/register
    phone      = Column(String(20), unique=True, index=True, nullable=True)   # Keep phone optional for backward compatibility
    password   = Column(String(200), nullable=False)                          # bcrypt hash
    role       = Column(String(20), default="user")                           # 'user' | 'admin'
    created_at = Column(DateTime, default=datetime.utcnow)

    # One user → many scans
    scans = relationship("ScanHistory", back_populates="user", cascade="all, delete-orphan")


# ─── Scan History Model ──────────────────────────────────────────────────────
class ScanHistory(Base):
    """Records every AI analysis performed. Linked to a user if logged in."""
    __tablename__ = "scan_history"

    id            = Column(Integer, primary_key=True, index=True)
    analysis_type = Column(String(50))
    crop_name     = Column(String(200), nullable=True)
    disease_name  = Column(String(200), nullable=True)
    severity      = Column(String(50),  nullable=True)
    result_summary= Column(String(500), nullable=True)
    full_result   = Column(Text)
    created_at    = Column(DateTime, default=datetime.utcnow)

    # Foreign key to User — nullable so existing scans are preserved
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    user    = relationship("User", back_populates="scans")


from sqlalchemy import Index
Index('idx_scan_user_id', ScanHistory.user_id)
Index('idx_scan_created_at', ScanHistory.created_at)
Index('idx_user_email', User.email)
