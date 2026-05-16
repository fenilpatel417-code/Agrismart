from fastapi import APIRouter, UploadFile, File, Form, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from database.db import get_db
from database.models import ScanHistory
from services.gemini_service import analyze_image

router = APIRouter(prefix="/api", tags=["detection"])

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/jpg"}
MAX_SIZE = 10 * 1024 * 1024  # 10MB


@router.post("/detect")
async def detect(
    file: UploadFile = File(...),
    analysis_type: str = Form(default="disease"),
    db: Session = Depends(get_db)
):
    # Validate file
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

    # Analyze with Gemini
    result = await analyze_image(image_bytes, analysis_type)

    if result["success"]:
        # Save to history
        scan = ScanHistory(
            analysis_type=result.get("analysis_label", analysis_type),
            crop_name=result.get("crop_name", "Unknown"),
            disease_name=result.get("disease_name"),
            severity=result.get("severity"),
            result_summary=result.get("summary", "")[:500],
            full_result=result.get("result", ""),
        )
        db.add(scan)
        db.commit()

    return JSONResponse(content=result)
