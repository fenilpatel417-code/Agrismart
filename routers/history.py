from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from database.db import get_db
from database.models import ScanHistory

router = APIRouter(prefix="/api", tags=["history"])


@router.get("/history")
def get_history(
    limit: int = Query(default=20, le=100),
    db: Session = Depends(get_db)
):
    scans = db.query(ScanHistory)\
        .order_by(ScanHistory.created_at.desc())\
        .limit(limit)\
        .all()

    return JSONResponse(content={
        "success": True,
        "history": [
            {
                "id": s.id,
                "analysis_type": s.analysis_type,
                "crop_name": s.crop_name,
                "disease_name": s.disease_name,
                "severity": s.severity,
                "result_summary": s.result_summary,
                "full_result": s.full_result,
                "created_at": s.created_at.strftime("%d %b %Y, %I:%M %p") if s.created_at else ""
            }
            for s in scans
        ]
    })


@router.delete("/history/{scan_id}")
def delete_scan(scan_id: int, db: Session = Depends(get_db)):
    scan = db.query(ScanHistory).filter(ScanHistory.id == scan_id).first()
    if not scan:
        return JSONResponse(status_code=404, content={"success": False, "error": "Not found"})
    db.delete(scan)
    db.commit()
    return JSONResponse(content={"success": True})
