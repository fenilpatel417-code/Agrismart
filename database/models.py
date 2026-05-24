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
    phone      = Column(String(20), unique=True, index=True, nullable=False)
    mobile     = Column(String(20), unique=True, index=True, nullable=True) # Mobile for OTP verification
    is_verified= Column(Integer, default=0) # 0 = false, 1 = true (using Integer/Boolean representation for safety)
    password   = Column(String(200), nullable=False)          # bcrypt hash
    role       = Column(String(20), default="user")           # 'user' | 'admin'
    otp        = Column(String(6), nullable=True)             # 6-digit OTP
    otp_expiry = Column(DateTime, nullable=True)              # OTP expiry time
    created_at = Column(DateTime, default=datetime.utcnow)

    # One user → many scans
    scans = relationship("ScanHistory", back_populates="user", cascade="all, delete-orphan")


# ─── OTP Verification Model ──────────────────────────────────────────────────
class OTPVerification(Base):
    """Stores OTP codes for mobile verification (registration & forgot password)"""
    __tablename__ = "otp_verification"

    id            = Column(Integer, primary_key=True)
    mobile        = Column(String(20), nullable=False, index=True)
    otp_hash      = Column(String(64), nullable=False)            # SHA-256 hashed OTP
    purpose       = Column(String(20), nullable=False)            # 'register' | 'forgot_password'
    attempts      = Column(Integer, default=0)                    # Wrong validation attempts
    is_used       = Column(Integer, default=0)                    # 0 = false, 1 = true
    blocked_until = Column(DateTime, nullable=True)               # Temporary block time if attempts >= 3
    expires_at    = Column(DateTime, nullable=False)
    created_at    = Column(DateTime, default=datetime.utcnow)


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
