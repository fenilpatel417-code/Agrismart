"""
services/auth_service.py
────────────────────────
Core authentication utilities:
  - Password hashing (bcrypt via passlib)
  - JWT creation & verification (python-jose)
  - Cookie helpers
  - Dependency functions for route protection
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Request, Depends
from fastapi.responses import RedirectResponse
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from database.db import get_db
from database.models import User
from dotenv import load_dotenv

load_dotenv()

# ─── Config ─────────────────────────────────────────────────────────────────
SECRET_KEY  = os.getenv("SECRET_KEY", "agrismart-super-secret-change-in-production")
ALGORITHM   = "HS256"
EXPIRE_DAYS = 7
COOKIE_NAME = "access_token"

# ─── Bcrypt context ──────────────────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ─── Password Helpers ────────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    """Return bcrypt hash of a plain-text password."""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if plain password matches the stored hash."""
    return pwd_context.verify(plain, hashed)


# ─── JWT Helpers ─────────────────────────────────────────────────────────────
def create_access_token(user_id: int, role: str) -> str:
    """
    Create a signed JWT containing user_id and role.
    Expires after EXPIRE_DAYS days.
    """
    expire  = datetime.now(timezone.utc) + timedelta(days=EXPIRE_DAYS)
    payload = {"sub": str(user_id), "role": role, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """
    Decode a JWT and return the payload dict.
    Returns None if the token is invalid or expired.
    """
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


# ─── Current User Helpers ────────────────────────────────────────────────────
def get_current_user(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    """
    Reads the JWT from the HTTP-only cookie.
    Returns the User ORM object if valid, otherwise None.
    Used as a FastAPI dependency.
    """
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    payload = decode_token(token)
    if not payload:
        return None
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    return user


def require_login(request: Request, db: Session = Depends(get_db)) -> User:
    """
    Dependency that raises a 302 redirect to /login
    if the user is not authenticated.
    """
    user = get_current_user(request, db)
    if not user:
        # Use an exception so FastAPI handles the redirect
        raise _redirect("/login")
    return user


def require_admin(request: Request, db: Session = Depends(get_db)) -> User:
    """
    Dependency that requires the user to be logged in AND have role='admin'.
    Redirects to /login if not authenticated, returns 403 page if not admin.
    """
    user = get_current_user(request, db)
    if not user:
        raise _redirect("/login")
    if user.role != "admin":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Admin access required.")
    return user


# ─── Cookie Helper ───────────────────────────────────────────────────────────
def set_auth_cookie(response, token: str):
    """Attach the JWT as an HTTP-only cookie to a response."""
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,          # Not accessible by JavaScript — prevents XSS
        max_age=60 * 60 * 24 * EXPIRE_DAYS,
        samesite="lax",
        secure=False,           # Set True in production with HTTPS
    )


def clear_auth_cookie(response):
    """Remove the auth cookie (logout)."""
    response.delete_cookie(key=COOKIE_NAME)


# ─── Internal Redirect Helper ────────────────────────────────────────────────
def _redirect(url: str):
    """Return a RedirectResponse wrapped as an HTTPException-compatible object."""
    from fastapi.exceptions import HTTPException
    # We raise an HTTPException with a special header trick.
    # Routes handle this via the redirect pattern.
    return RedirectResponse(url=url, status_code=302)
