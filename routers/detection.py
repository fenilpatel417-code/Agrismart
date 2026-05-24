"""
routers/detection.py
────────────────────
Handles crop image analysis. Login required.
Scans are saved linked to the logged-in user's ID.
"""

from fastapi import APIRouter, UploadFile, File, Form, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from database.db import get_db
from database.models import ScanHistory
from services.gemini_service import analyze_image
from services.auth_service import get_current_user

router = APIRouter(prefix="/api", tags=["detection"])

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/jpg"}
MAX_SIZE      = 10 * 1024 * 1024  # 10 MB


@router.post("/detect")
async def detect(
    request      : Request,
    file         : UploadFile = File(...),
    analysis_type: str        = Form(default="disease"),
    language     : str        = Form(default="en"),
    db           : Session    = Depends(get_db),
):
    # ── Auth check ──────────────────────────────────────────────
    current_user = get_current_user(request, db)
    if not current_user:
        return JSONResponse(
            status_code=401,
            content={"success": False, "error": "Please log in to analyze crops.", "redirect": "/login"}
        )

    # ── File validation ─────────────────────────────────────────
    if file.content_type not in ALLOWED_TYPES:
        return JSONResponse(status_code=400, content={
            "success": False,
            "error": "Please upload a JPG, PNG, or WebP image."
        })

    image_bytes = await file.read()

    if len(image_bytes) > MAX_SIZE:
        return JSONResponse(status_code=400, content={
            "success": False,
            "error": "Image too large. Please upload an image under 10MB."
        })

    # ── Analyze with Gemini ─────────────────────────────────────
    result = await analyze_image(image_bytes, analysis_type, language)

    if result["success"]:
        # Save to history, linked to logged-in user
        scan = ScanHistory(
            analysis_type = result.get("analysis_label", analysis_type),
            crop_name     = result.get("crop_name", "Unknown"),
            disease_name  = result.get("disease_name"),
            severity      = result.get("severity"),
            result_summary= result.get("summary", "")[:500],
            full_result   = result.get("result", ""),
            user_id       = current_user.id,   # ← link to user
        )
        db.add(scan)
        db.commit()
        return JSONResponse(content=result)
    
    return JSONResponse(status_code=400, content=result)
