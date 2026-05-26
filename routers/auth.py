"""
routers/auth.py
───────────────
Authentication + user-facing page routes:
  GET/POST /login      — Login page
  GET/POST /register   — Register page
  GET      /logout     — Clear cookie and redirect
  GET      /dashboard  — Logged-in user's scan history
  GET      /admin      — Admin panel (admin role only)

Admin API routes:
  DELETE /admin/users/{id}            — Delete user + their scans
  POST   /admin/users/{id}/toggle-role — Promote/demote admin
  DELETE /admin/scans/{id}            — Delete any scan
"""

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
import random
from datetime import datetime, timedelta

from database.db import get_db
from database.models import User, ScanHistory
from services.auth_service import (
    hash_password, verify_password,
    create_access_token, get_current_user,
    set_auth_cookie, clear_auth_cookie,
)

router    = APIRouter(tags=["auth"])
templates = Jinja2Templates(directory="templates")


# ═══════════════════════════════════════════════════════════════
# REGISTER (OTP-verified 2-step flow)
# ═══════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════
# REGISTER (OTP-verified 2-step flow)
# ═══════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════
# REGISTER (Direct flow without OTP)
# ═══════════════════════════════════════════════════════════════

@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, db: Session = Depends(get_db)):
    """Show registration form. Redirect to dashboard if already logged in."""
    user = get_current_user(request, db)
    if user:
        return RedirectResponse("/dashboard", status_code=302)
    return templates.TemplateResponse("register.html", {"request": request, "error": None})


@router.post("/register", response_class=HTMLResponse)
async def register_submit(
    request : Request,
    name    : str = Form(...),
    email   : str = Form(...),
    password: str = Form(...),
    db      : Session = Depends(get_db),
):
    """Register user directly and redirect to login."""
    name_clean = name.strip()
    email_clean = email.strip().lower()

    # Validate email
    if "@" not in email_clean:
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": "Please enter a valid email address."
        })

    # Check if email already exists
    existing = db.query(User).filter(User.email == email_clean).first()
    if existing:
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": "This email address is already registered."
        })

    # Validate password length
    if len(password) < 6:
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": "Password must be at least 6 characters long."
        })

    # Create new user directly (No OTP)
    new_user = User(
        name     = name_clean,
        email    = email_clean,
        password = hash_password(password),
        role     = "user",
    )
    db.add(new_user)
    db.commit()

    return RedirectResponse("/login?registered=1", status_code=302)


# ═══════════════════════════════════════════════════════════════
# LOGIN
# ═══════════════════════════════════════════════════════════════

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, db: Session = Depends(get_db)):
    """Show login form. Redirect to dashboard if already logged in."""
    user = get_current_user(request, db)
    if user:
        return RedirectResponse("/dashboard", status_code=302)
    registered = request.query_params.get("registered")
    reset_success = request.query_params.get("reset_success")
    success_msg = None
    if registered:
        success_msg = "Account created! Please log in."
    elif reset_success:
        success_msg = "Password reset successful! Please log in."
        
    return templates.TemplateResponse("login.html", {
        "request"   : request,
        "error"     : None,
        "success"   : success_msg,
    })


@router.post("/login", response_class=HTMLResponse)
async def login_submit(
    request : Request,
    phone   : str = Form(...),
    password: str = Form(...),
    db      : Session = Depends(get_db),
):
    """Handle login form submission. Supports both email and phone login."""
    phone_clean = phone.strip()
    user = db.query(User).filter(
        (User.email == phone_clean.lower()) | 
        (User.phone == phone_clean)
    ).first()

    if not user or not verify_password(password, user.password):
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error"  : "Invalid email/mobile number or password. Please try again.",
            "success": None,
        })

    # Create token and set HTTP-only cookie
    token    = create_access_token(user.id, user.role)
    redirect = RedirectResponse("/dashboard", status_code=302)
    set_auth_cookie(redirect, token)
    return redirect


# ═══════════════════════════════════════════════════════════════
# LOGOUT
# ═══════════════════════════════════════════════════════════════

@router.get("/logout")
async def logout():
    """Clear auth cookie and redirect to login page."""
    response = RedirectResponse("/login", status_code=302)
    clear_auth_cookie(response)
    return response


# ═══════════════════════════════════════════════════════════════
# FORGOT PASSWORD & PASSWORD RESET (Direct flow without OTP)
# ═══════════════════════════════════════════════════════════════

@router.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request, db: Session = Depends(get_db)):
    """Render direct forgot password/reset page."""
    user = get_current_user(request, db)
    if user:
        return RedirectResponse("/dashboard", status_code=302)
    return templates.TemplateResponse("forgot_password.html", {"request": request, "error": None})


@router.post("/forgot-password", response_class=HTMLResponse)
async def forgot_password_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db),
):
    """Directly reset password using Email and redirect to login."""
    email_clean = email.strip().lower()

    # Find the user by email
    user = db.query(User).filter(User.email == email_clean).first()
    if not user:
        return templates.TemplateResponse("forgot_password.html", {
            "request": request,
            "error": "This email address is not registered."
        })

    # Validate passwords match
    if password != confirm_password:
        return templates.TemplateResponse("forgot_password.html", {
            "request": request,
            "error": "Passwords do not match. Please try again."
        })

    # Validate password length
    if len(password) < 6:
        return templates.TemplateResponse("forgot_password.html", {
            "request": request,
            "error": "Password must be at least 6 characters long."
        })

    # Direct password reset (No OTP)
    user.password = hash_password(password)
    db.commit()

    return RedirectResponse("/login?reset_success=1", status_code=302)


# ═══════════════════════════════════════════════════════════════
# USER DASHBOARD
# ═══════════════════════════════════════════════════════════════

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    """Personal scan history page. Login required."""
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)

    # Get this user's scans, newest first
    scans = (
        db.query(ScanHistory)
        .filter(ScanHistory.user_id == user.id)
        .order_by(ScanHistory.created_at.desc())
        .all()
    )
    return templates.TemplateResponse("dashboard.html", {
        "request"     : request,
        "current_user": user,
        "scans"       : scans,
    })


# ═══════════════════════════════════════════════════════════════
# ADMIN PANEL
# ═══════════════════════════════════════════════════════════════

@router.get("/admin", response_class=HTMLResponse)
async def admin_panel(
    request: Request,
    page: int = 1,
    db: Session = Depends(get_db)
):
    """Admin panel. Requires role='admin'."""
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if user.role != "admin":
        return templates.TemplateResponse("403.html", {"request": request, "current_user": user}, status_code=403)

    # Stats
    total_users = db.query(func.count(User.id)).scalar() or 0
    total_scans = db.query(func.count(ScanHistory.id)).scalar() or 0

    # All users with their scan counts
    users = db.query(User).order_by(User.created_at.desc()).all()
    user_scan_counts = {
        row.user_id: row.count
        for row in db.query(ScanHistory.user_id, func.count(ScanHistory.id).label("count"))
                      .group_by(ScanHistory.user_id).all()
    }

    # Paginate recent scans: max 100 scans, 20 items per page
    limit = 20
    offset = (max(1, page) - 1) * limit
    
    total_admin_scans = min(100, total_scans)
    total_pages = (total_admin_scans + limit - 1) // limit

    if offset >= 100:
        recent_scans = []
    else:
        current_limit = min(limit, 100 - offset)
        recent_scans = (
            db.query(ScanHistory)
            .order_by(ScanHistory.created_at.desc())
            .offset(offset)
            .limit(current_limit)
            .all()
        )

    return templates.TemplateResponse("admin.html", {
        "request"        : request,
        "current_user"   : user,
        "total_users"    : total_users,
        "total_scans"    : total_scans,
        "users"          : users,
        "user_scan_counts": user_scan_counts,
        "recent_scans"   : recent_scans,
        "page"           : page,
        "total_pages"    : total_pages,
    })


# ═══════════════════════════════════════════════════════════════
# ADMIN API — User Management
# ═══════════════════════════════════════════════════════════════

@router.delete("/admin/users/{user_id}")
async def admin_delete_user(user_id: int, request: Request, db: Session = Depends(get_db)):
    """Admin only: Delete a user and all their scans."""
    admin = get_current_user(request, db)
    if not admin or admin.role != "admin":
        return JSONResponse(status_code=403, content={"success": False, "error": "Forbidden"})
    if admin.id == user_id:
        return JSONResponse(status_code=400, content={"success": False, "error": "Cannot delete yourself."})

    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        return JSONResponse(status_code=404, content={"success": False, "error": "User not found."})

    db.delete(target)   # cascade deletes their scans too
    db.commit()
    return JSONResponse(content={"success": True})


@router.post("/admin/users/{user_id}/toggle-role")
async def admin_toggle_role(user_id: int, request: Request, db: Session = Depends(get_db)):
    """Admin only: Promote user → admin or demote admin → user."""
    admin = get_current_user(request, db)
    if not admin or admin.role != "admin":
        return JSONResponse(status_code=403, content={"success": False, "error": "Forbidden"})
    if admin.id == user_id:
        return JSONResponse(status_code=400, content={"success": False, "error": "Cannot change your own role."})

    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        return JSONResponse(status_code=404, content={"success": False, "error": "User not found."})

    target.role = "admin" if target.role == "user" else "user"
    db.commit()
    return JSONResponse(content={"success": True, "new_role": target.role})


@router.delete("/admin/scans/{scan_id}")
async def admin_delete_scan(scan_id: int, request: Request, db: Session = Depends(get_db)):
    """Admin only: Delete any scan."""
    admin = get_current_user(request, db)
    if not admin or admin.role != "admin":
        return JSONResponse(status_code=403, content={"success": False, "error": "Forbidden"})

    scan = db.query(ScanHistory).filter(ScanHistory.id == scan_id).first()
    if not scan:
        return JSONResponse(status_code=404, content={"success": False, "error": "Scan not found."})

    db.delete(scan)
    db.commit()
    return JSONResponse(content={"success": True})
