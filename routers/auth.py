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
from services.otp_service import (
    generate_otp, send_otp_sms, save_otp, verify_otp, can_send_otp
)

router    = APIRouter(tags=["auth"])
templates = Jinja2Templates(directory="templates")


# ═══════════════════════════════════════════════════════════════
# REGISTER (OTP-verified 2-step flow)
# ═══════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════
# REGISTER (OTP-verified 2-step flow)
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

    # Check if phone already exists in database
    existing = db.query(User).filter((User.phone == phone_clean) | (User.mobile == phone_clean)).first()
    if existing:
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": "Mobile number is already registered."
        })

    # Validate password length
    if len(password) < 6:
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": "Password must be at least 6 characters long."
        })

    # Rate Limit Check
    allowed, reason = can_send_otp(db, phone_clean)
    if not allowed:
        if reason == "blocked":
            error_msg = "Mobile number is blocked. Please try again after 30 minutes."
        elif reason == "hourly_limit":
            error_msg = "Maximum OTP requests exceeded. Limit 3 per hour."
        else:
            error_msg = "Daily OTP request limit exceeded. Limit 5 per day."
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": error_msg
        })

    # Generate 6-digit OTP and store pending registration in session
    otp = generate_otp()
    
    # Session data to store temporarily (Task 5)
    request.session["pending_user"] = {
        "name": name.strip(),
        "mobile": phone_clean,
        "password_hash": hash_password(password),
        "purpose": "register"
    }

    # Save to database and dispatch SMS (falls back to console sandbox if Twilio is not configured)
    save_otp(db, phone_clean, otp, "register")
    send_otp_sms(phone_clean, otp, "register")

    return RedirectResponse("/verify-otp", status_code=302)


@router.get("/verify-otp", response_class=HTMLResponse)
async def verify_otp_page(
    request: Request,
    db: Session = Depends(get_db),
):
    """Show OTP verification form for new registration."""
    user = get_current_user(request, db)
    if user:
        return RedirectResponse("/dashboard", status_code=302)

    pending = request.session.get("pending_user")
    if not pending or pending.get("purpose") != "register":
        return RedirectResponse("/register", status_code=302)

    mobile = pending["mobile"]
    masked_mobile = "XXXXXX" + mobile[-4:]

    return templates.TemplateResponse("verify_otp.html", {
        "request": request,
        "mobile": mobile,
        "masked_mobile": masked_mobile,
        "error": None,
    })


@router.post("/verify-otp", response_class=HTMLResponse)
async def verify_otp_submit(
    request: Request,
    db: Session = Depends(get_db),
):
    """Step 2: Verify OTP and create the user account."""
    user = get_current_user(request, db)
    if user:
        return RedirectResponse("/dashboard", status_code=302)

    pending = request.session.get("pending_user")
    if not pending or pending.get("purpose") != "register":
        return RedirectResponse("/register", status_code=302)

    mobile = pending["mobile"]
    masked_mobile = "XXXXXX" + mobile[-4:]

    # Combine 6 digits of OTP input (flexible paste/single support)
    form_data = await request.form()
    otp_digits = [form_data.get(f"otp{i}", "").strip() for i in range(1, 7)]
    otp_clean = "".join(otp_digits)
    if not otp_clean:
        otp_clean = form_data.get("otp", "").strip()

    if not otp_clean or len(otp_clean) != 6 or not otp_clean.isdigit():
        return templates.TemplateResponse("verify_otp.html", {
            "request": request,
            "mobile": mobile,
            "masked_mobile": masked_mobile,
            "error": "Please enter a valid 6-digit OTP code."
        })

    # Call verify OTP service
    status = verify_otp(db, mobile, otp_clean, "register")

    if status == "verified":
        # Create user account since OTP is verified
        new_user = User(
            name     = pending["name"],
            phone    = mobile, # Populate phone for backward compatibility
            mobile   = mobile,
            password = pending["password_hash"],
            role     = "user",
            is_verified = 1 # Marked as verified
        )
        db.add(new_user)
        db.commit()

        # Clean up session
        request.session.pop("pending_user", None)
        return RedirectResponse("/login?registered=1", status_code=302)

    elif status == "blocked":
        error_msg = "Too many failed attempts. This mobile number is blocked for 30 minutes."
    elif status == "expired":
        error_msg = "OTP has expired. Please request a new one."
    elif status == "wrong":
        # Retrieve the attempts count to give feedback
        record = db.query(OTPVerification).filter(
            OTPVerification.mobile == mobile,
            OTPVerification.purpose == "register"
        ).first()
        attempts_left = 3 - (record.attempts if record else 0)
        error_msg = f"Invalid OTP. Please try again. ({attempts_left} attempts remaining)"
    else:
        error_msg = "Invalid or missing registration OTP session. Please try again."

    return templates.TemplateResponse("verify_otp.html", {
        "request": request,
        "mobile": mobile,
        "masked_mobile": masked_mobile,
        "error": error_msg
    })


@router.post("/resend-otp", response_class=HTMLResponse)
async def resend_otp_submit(
    request: Request,
    db: Session = Depends(get_db),
):
    """Resend registration OTP (enforces rate-limiting)."""
    pending = request.session.get("pending_user")
    if not pending or pending.get("purpose") != "register":
        return RedirectResponse("/register", status_code=302)

    mobile = pending["mobile"]
    masked_mobile = "XXXXXX" + mobile[-4:]

    # Check resend eligibility
    allowed, reason = can_send_otp(db, mobile)
    if not allowed:
        if reason == "blocked":
            error_msg = "Mobile number is blocked. Please try again after 30 minutes."
        elif reason == "hourly_limit":
            error_msg = "Maximum OTP requests exceeded. Limit 3 per hour."
        else:
            error_msg = "Daily OTP request limit exceeded. Limit 5 per day."

        return templates.TemplateResponse("verify_otp.html", {
            "request": request,
            "mobile": mobile,
            "masked_mobile": masked_mobile,
            "error": error_msg
        })

    # Generate and send new OTP
    otp = generate_otp()
    save_otp(db, mobile, otp, "register")
    send_otp_sms(mobile, otp, "register")

    return templates.TemplateResponse("verify_otp.html", {
        "request": request,
        "mobile": mobile,
        "masked_mobile": masked_mobile,
        "success": "OTP resent successfully!"
    })


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

    # Find the user by phone or mobile
    user = db.query(User).filter((User.phone == phone_clean) | (User.mobile == phone_clean)).first()
    if not user:
        return templates.TemplateResponse("forgot_password.html", {
            "request": request,
            "phone": phone_clean,
            "error": "This mobile number is not registered."
        })

    # Rate Limit Check
    allowed, reason = can_send_otp(db, phone_clean)
    if not allowed:
        if reason == "blocked":
            error_msg = "Mobile number is blocked. Please try again after 30 minutes."
        elif reason == "hourly_limit":
            error_msg = "Maximum OTP requests exceeded. Limit 3 per hour."
        else:
            error_msg = "Daily OTP request limit exceeded. Limit 5 per day."
        return templates.TemplateResponse("forgot_password.html", {
            "request": request,
            "phone": phone_clean,
            "error": error_msg
        })

    # Generate 6-digit OTP and store forgot password details in session
    otp = generate_otp()
    
    # Session data to store temporarily
    request.session["forgot_password_mobile"] = phone_clean

    # Save to database and dispatch SMS (falls back to console sandbox if Twilio is not configured)
    save_otp(db, phone_clean, otp, "forgot_password")
    send_otp_sms(phone_clean, otp, "forgot_password")

    return RedirectResponse("/verify-forgot-otp", status_code=302)


@router.get("/verify-forgot-otp", response_class=HTMLResponse)
async def verify_forgot_otp_page(
    request: Request,
    db: Session = Depends(get_db),
):
    """Show OTP verification form for password reset."""
    user = get_current_user(request, db)
    if user:
        return RedirectResponse("/dashboard", status_code=302)

    mobile = request.session.get("forgot_password_mobile")
    if not mobile:
        return RedirectResponse("/forgot-password", status_code=302)

    masked_mobile = "XXXXXX" + mobile[-4:]

    return templates.TemplateResponse("verify_forgot_otp.html", {
        "request": request,
        "mobile": mobile,
        "masked_mobile": masked_mobile,
        "error": None,
    })


@router.post("/verify-forgot-otp", response_class=HTMLResponse)
async def verify_forgot_otp_submit(
    request: Request,
    db: Session = Depends(get_db),
):
    """Verify forgot password OTP."""
    user = get_current_user(request, db)
    if user:
        return RedirectResponse("/dashboard", status_code=302)

    mobile = request.session.get("forgot_password_mobile")
    if not mobile:
        return RedirectResponse("/forgot-password", status_code=302)

    masked_mobile = "XXXXXX" + mobile[-4:]

    # Combine 6 digits of OTP input (flexible paste/single support)
    form_data = await request.form()
    otp_digits = [form_data.get(f"otp{i}", "").strip() for i in range(1, 7)]
    otp_clean = "".join(otp_digits)
    if not otp_clean:
        otp_clean = form_data.get("otp", "").strip()

    if not otp_clean or len(otp_clean) != 6 or not otp_clean.isdigit():
        return templates.TemplateResponse("verify_forgot_otp.html", {
            "request": request,
            "mobile": mobile,
            "masked_mobile": masked_mobile,
            "error": "Please enter a valid 6-digit OTP code."
        })

    # Call verify OTP service
    status = verify_otp(db, mobile, otp_clean, "forgot_password")

    if status == "verified":
        # Store authorization token in session to allow access to reset password page
        request.session["reset_authorized"] = True
        return RedirectResponse("/reset-password", status_code=302)

    elif status == "blocked":
        error_msg = "Too many failed attempts. This mobile number is blocked for 30 minutes."
    elif status == "expired":
        error_msg = "OTP has expired. Please request a new one."
    elif status == "wrong":
        # Retrieve the attempts count to give feedback
        record = db.query(OTPVerification).filter(
            OTPVerification.mobile == mobile,
            OTPVerification.purpose == "forgot_password"
        ).first()
        attempts_left = 3 - (record.attempts if record else 0)
        error_msg = f"Invalid OTP. Please try again. ({attempts_left} attempts remaining)"
    else:
        error_msg = "Invalid or missing recovery session. Please try again."

    return templates.TemplateResponse("verify_forgot_otp.html", {
        "request": request,
        "mobile": mobile,
        "masked_mobile": masked_mobile,
        "error": error_msg
    })


@router.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page(
    request: Request,
    db: Session = Depends(get_db)
):
    """Render reset password form."""
    user = get_current_user(request, db)
    if user:
        return RedirectResponse("/dashboard", status_code=302)

    mobile = request.session.get("forgot_password_mobile")
    authorized = request.session.get("reset_authorized")

    # Access protection: must have verified OTP first
    if not mobile or not authorized:
        return RedirectResponse("/forgot-password", status_code=302)

    return templates.TemplateResponse("reset_password.html", {
        "request": request,
        "phone": mobile,
        "error": None
    })


@router.post("/reset-password", response_class=HTMLResponse)
async def reset_password_submit(
    request: Request,
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Handle password reset verification and database update."""
    mobile = request.session.get("forgot_password_mobile")
    authorized = request.session.get("reset_authorized")

    # Access protection: must have verified OTP first
    if not mobile or not authorized:
        return RedirectResponse("/forgot-password", status_code=302)

    if password != confirm_password:
        return templates.TemplateResponse("reset_password.html", {
            "request": request,
            "phone": mobile,
            "error": "Passwords do not match. Please try again."
        })

    if len(password) < 6:
        return templates.TemplateResponse("reset_password.html", {
            "request": request,
            "phone": mobile,
            "error": "Password must be at least 6 characters long."
        })

    user = db.query(User).filter((User.phone == mobile) | (User.mobile == mobile)).first()
    if not user:
        return RedirectResponse("/forgot-password", status_code=302)

    # Valid authorization -> Update password
    user.password = hash_password(password)
    db.commit()

    # Clear recovery session variables
    request.session.pop("forgot_password_mobile", None)
    request.session.pop("reset_authorized", None)

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
