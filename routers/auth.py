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

# In-memory pending registrations: { phone: { name, password_hash, otp, otp_expiry } }
_pending_registrations = {}

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
    phone   : str = Form(...),
    password: str = Form(...),
    db      : Session = Depends(get_db),
):
    """Step 1: Validate inputs, generate OTP, and redirect to verification page."""
    # Validate phone number
    phone_clean = phone.strip()
    if not phone_clean.isdigit() or len(phone_clean) != 10:
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": "Mobile number must be exactly 10 digits."
        })

    # Check if phone already exists
    existing = db.query(User).filter(User.phone == phone_clean).first()
    if existing:
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": "An account with this mobile number already exists. Please log in."
        })

    # Validate password length
    if len(password) < 6:
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": "Password must be at least 6 characters long."
        })

    # Generate 6-digit OTP and store pending registration
    otp = f"{random.randint(100000, 999999)}"
    _pending_registrations[phone_clean] = {
        "name": name.strip(),
        "password_hash": hash_password(password),
        "otp": otp,
        "otp_expiry": datetime.utcnow() + timedelta(minutes=5),
    }

    # Simulated SMS for local testing
    print(f"[REG OTP] Simulated SMS to +91 {phone_clean} - Code: {otp}")

    return RedirectResponse(f"/verify-registration?phone={phone_clean}", status_code=302)


@router.get("/verify-registration", response_class=HTMLResponse)
async def verify_registration_page(
    request: Request,
    phone: str = None,
    db: Session = Depends(get_db),
):
    """Show OTP verification form for new registration."""
    user = get_current_user(request, db)
    if user:
        return RedirectResponse("/dashboard", status_code=302)
    return templates.TemplateResponse("verify_registration.html", {
        "request": request,
        "phone": phone,
        "error": None,
    })


@router.post("/verify-registration", response_class=HTMLResponse)
async def verify_registration_submit(
    request: Request,
    phone: str = Form(...),
    otp: str   = Form(...),
    db: Session = Depends(get_db),
):
    """Step 2: Verify OTP and create the user account."""
    phone_clean = phone.strip()
    otp_clean = otp.strip()

    pending = _pending_registrations.get(phone_clean)
    if not pending:
        return templates.TemplateResponse("verify_registration.html", {
            "request": request,
            "phone": phone_clean,
            "error": "No pending registration found. Please register again.",
        })

    # Check OTP expiry
    if datetime.utcnow() > pending["otp_expiry"]:
        del _pending_registrations[phone_clean]
        return templates.TemplateResponse("verify_registration.html", {
            "request": request,
            "phone": phone_clean,
            "error": "OTP has expired. Please register again.",
        })

    # Verify OTP
    if otp_clean != pending["otp"]:
        return templates.TemplateResponse("verify_registration.html", {
            "request": request,
            "phone": phone_clean,
            "error": "Invalid OTP. Please check the code and try again.",
        })

    # OTP verified — create the user account
    new_user = User(
        name     = pending["name"],
        phone    = phone_clean,
        password = pending["password_hash"],
        role     = "user",
    )
    db.add(new_user)
    db.commit()

    # Clean up pending registration
    del _pending_registrations[phone_clean]

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
    """Handle login form submission. Set JWT cookie on success."""
    phone_clean = phone.strip()
    user = db.query(User).filter(User.phone == phone_clean).first()

    if not user or not verify_password(password, user.password):
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error"  : "Invalid mobile number or password. Please try again.",
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
# FORGOT PASSWORD & OTP RECOVERY
# ═══════════════════════════════════════════════════════════════

@router.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request, db: Session = Depends(get_db)):
    """Render forgot password page."""
    user = get_current_user(request, db)
    if user:
        return RedirectResponse("/dashboard", status_code=302)
    return templates.TemplateResponse("forgot_password.html", {"request": request, "error": None})


@router.post("/forgot-password", response_class=HTMLResponse)
async def forgot_password_submit(
    request: Request,
    phone: str = Form(...),
    db: Session = Depends(get_db),
):
    """Handle request to send password reset OTP."""
    phone_clean = phone.strip()
    if not phone_clean.isdigit() or len(phone_clean) != 10:
        return templates.TemplateResponse("forgot_password.html", {
            "request": request,
            "phone": phone_clean,
            "error": "Mobile number must be exactly 10 digits."
        })

    user = db.query(User).filter(User.phone == phone_clean).first()
    if not user:
        return templates.TemplateResponse("forgot_password.html", {
            "request": request,
            "phone": phone_clean,
            "error": "This mobile number is not registered."
        })

    # Generate 6-digit OTP code and set 5-minute expiry
    otp = f"{random.randint(100000, 999999)}"
    user.otp = otp
    user.otp_expiry = datetime.utcnow() + timedelta(minutes=5)
    db.commit()

    # Log/Print Simulated SMS to console for local testing
    print(f"[OTP] Simulated SMS to +91 {phone_clean} - Code: {otp}")

    return RedirectResponse(f"/reset-password?phone={phone_clean}", status_code=302)


@router.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page(
    request: Request,
    phone: str = None,
    db: Session = Depends(get_db)
):
    """Render reset password form."""
    user = get_current_user(request, db)
    if user:
        return RedirectResponse("/dashboard", status_code=302)
    return templates.TemplateResponse("reset_password.html", {
        "request": request,
        "phone": phone,
        "error": None
    })


@router.post("/reset-password", response_class=HTMLResponse)
async def reset_password_submit(
    request: Request,
    phone: str = Form(...),
    otp: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Handle password reset verification and database update."""
    phone_clean = phone.strip()
    otp_clean = otp.strip()

    user = db.query(User).filter(User.phone == phone_clean).first()
    if not user:
        return templates.TemplateResponse("reset_password.html", {
            "request": request,
            "phone": phone_clean,
            "error": "Mobile number is not registered."
        })

    # Check OTP and Expiry
    if not user.otp or user.otp != otp_clean:
        return templates.TemplateResponse("reset_password.html", {
            "request": request,
            "phone": phone_clean,
            "error": "Invalid OTP code. Please try again."
        })

    if not user.otp_expiry or user.otp_expiry < datetime.utcnow():
        return templates.TemplateResponse("reset_password.html", {
            "request": request,
            "phone": phone_clean,
            "error": "OTP has expired. Please request a new one."
        })

    # Valid OTP -> Update password
    user.password = hash_password(password)
    user.otp = None
    user.otp_expiry = None
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
async def admin_panel(request: Request, db: Session = Depends(get_db)):
    """Admin panel. Requires role='admin'."""
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if user.role != "admin":
        return templates.TemplateResponse("403.html", {"request": request, "current_user": user}, status_code=403)

    # Stats
    total_users = db.query(func.count(User.id)).scalar()
    total_scans = db.query(func.count(ScanHistory.id)).scalar()

    # All users with their scan counts
    users = db.query(User).order_by(User.created_at.desc()).all()
    user_scan_counts = {
        row.user_id: row.count
        for row in db.query(ScanHistory.user_id, func.count(ScanHistory.id).label("count"))
                      .group_by(ScanHistory.user_id).all()
    }

    # Recent 10 scans across all users
    recent_scans = (
        db.query(ScanHistory)
        .order_by(ScanHistory.created_at.desc())
        .limit(50)
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
