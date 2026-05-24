from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from contextlib import asynccontextmanager
from database.db import engine, Base
from routers import detection, chatbot, history, auth, market
from services.auth_service import get_current_user
from database.db import SessionLocal
import os


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all tables on startup (safe — won't drop existing data)
    Base.metadata.create_all(bind=engine)
    os.makedirs("static/uploads", exist_ok=True)
    yield


app = FastAPI(
    title="AgriSmart",
    description="AI-powered crop disease detection & advisory platform",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ─── Register Routers ────────────────────────────────────────────────────────
app.include_router(detection.router)
app.include_router(chatbot.router)
app.include_router(history.router)
app.include_router(auth.router)
app.include_router(market.router)


# ─── Helper: get current user for page templates ─────────────────────────────
def _get_user(request: Request):
    """Reads the JWT cookie and returns the User object or None."""
    db   = SessionLocal()
    user = get_current_user(request, db)
    db.close()
    return user


# ─── Public Pages (no login required) ────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    user = _get_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse("index.html", {
        "request": request, "current_user": user
    })


# ─── Protected Pages (login required — redirect to /login if not) ─────────────

@app.get("/detect", response_class=HTMLResponse)
async def detect_page(request: Request):
    user = _get_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse("detect.html", {
        "request": request, "current_user": user
    })


@app.get("/chatbot", response_class=HTMLResponse)
async def chatbot_page(request: Request):
    user = _get_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse("chatbot.html", {
        "request": request, "current_user": user
    })


@app.get("/history", response_class=HTMLResponse)
async def history_page(request: Request):
    user = _get_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse("history.html", {
        "request": request, "current_user": user
    })


# ─── 403 Forbidden Page ───────────────────────────────────────────────────────
@app.exception_handler(403)
async def forbidden_handler(request: Request, exc):
    return templates.TemplateResponse("403.html", {
        "request": request, "current_user": _get_user(request)
    }, status_code=403)
