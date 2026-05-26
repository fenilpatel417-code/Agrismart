"""
routers/history.py
──────────────────
Scan history API. Login required.
- Regular users see only their own scans.
- Admins see all scans.
- Users can only delete their own scans; admins can delete any.
"""

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from database.db import get_db
from database.models import ScanHistory
from services.auth_service import get_current_user

router = APIRouter(prefix="/api", tags=["history"])


@router.get("/history")
def get_history(
    request: Request,
    limit  : int     = Query(default=20, le=100),
    db     : Session = Depends(get_db),
):
    """Return scan history. Filters by user unless admin. Capped at 50 for regular users, 100 for admin."""
    current_user = get_current_user(request, db)
    if not current_user:
        return JSONResponse(status_code=401, content={"success": False, "error": "Login required."})

    from sqlalchemy import desc

    # Specific column projection to make the query extremely fast
    query = db.query(
        ScanHistory.id,
        ScanHistory.analysis_type,
        ScanHistory.crop_name,
        ScanHistory.disease_name,
        ScanHistory.severity,
        ScanHistory.result_summary,
        ScanHistory.full_result,
        ScanHistory.created_at
    )

    if current_user.role == "admin":
        scans = query.order_by(desc(ScanHistory.created_at)).limit(100).all()
    else:
        scans = query.filter(ScanHistory.user_id == current_user.id).order_by(desc(ScanHistory.created_at)).limit(50).all()

    return JSONResponse(content={
        "success": True,
        "history": [
            {
                "id"           : s.id,
                "analysis_type": s.analysis_type,
                "crop_name"    : s.crop_name,
                "disease_name" : s.disease_name,
                "severity"     : s.severity,
                "result_summary": s.result_summary,
                "full_result"  : s.full_result,
                "created_at"   : s.created_at.strftime("%d %b %Y, %I:%M %p") if s.created_at else "",
            }
            for s in scans
        ]
    })


@router.delete("/history/{scan_id}")
def delete_scan(scan_id: int, request: Request, db: Session = Depends(get_db)):
    """Delete a scan. Users can delete their own; admins can delete any."""
    current_user = get_current_user(request, db)
    if not current_user:
        return JSONResponse(status_code=401, content={"success": False, "error": "Login required."})

    scan = db.query(ScanHistory).filter(ScanHistory.id == scan_id).first()
    if not scan:
        return JSONResponse(status_code=404, content={"success": False, "error": "Not found."})

    # Permission check: user can only delete their own scans
    if current_user.role != "admin" and scan.user_id != current_user.id:
        return JSONResponse(status_code=403, content={"success": False, "error": "Not allowed."})

    db.delete(scan)
    db.commit()
    return JSONResponse(content={"success": True})
