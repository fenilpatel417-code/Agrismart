from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from services.gemini_service import chat_with_agribot

router = APIRouter(prefix="/api", tags=["chatbot"])


class ChatRequest(BaseModel):
    message: str
    history: list = []


@router.post("/chat")
async def chat(request: ChatRequest):
    if not request.message.strip():
        return JSONResponse(status_code=400, content={
            "success": False,
            "error": "Message cannot be empty."
        })

    response = await chat_with_agribot(request.message.strip(), request.history)

    return JSONResponse(content={
        "success": True,
        "response": response
    })
