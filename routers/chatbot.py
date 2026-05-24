"""
routers/chatbot.py
──────────────────
AI chatbot endpoint. Login required.
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.db import get_db
from services.gemini_service import chat_with_agribot
from services.auth_service import get_current_user

router = APIRouter(prefix="/api", tags=["chatbot"])


class ChatRequest(BaseModel):
    message: str
    history: list = []
    language: str = "en"


@router.post("/chat")
async def chat(payload: ChatRequest, request: Request, db: Session = Depends(get_db)):
    # ── Auth check ───────────────────────────────────────────────
    current_user = get_current_user(request, db)
    if not current_user:
        return JSONResponse(
            status_code=401,
            content={"success": False, "error": "Please log in to use AgriBot.", "redirect": "/login"}
        )

    if not payload.message.strip():
        return JSONResponse(status_code=400, content={
            "success": False,
            "error": "Message cannot be empty."
        })

    response = await chat_with_agribot(payload.message.strip(), payload.history, payload.language)

    return JSONResponse(content={"success": True, "response": response})
