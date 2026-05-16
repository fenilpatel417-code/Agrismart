from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from database.db import engine, Base
from routers import detection, chatbot, history
import os


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    os.makedirs("static/uploads", exist_ok=True)
    yield


app = FastAPI(
    title="AgriSmart",
    description="AI-powered crop disease detection & advisory platform",
    version="1.0.0",
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

app.include_router(detection.router)
app.include_router(chatbot.router)
app.include_router(history.router)


@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/detect")
async def detect_page(request: Request):
    return templates.TemplateResponse("detect.html", {"request": request})


@app.get("/chatbot")
async def chatbot_page(request: Request):
    return templates.TemplateResponse("chatbot.html", {"request": request})


@app.get("/history")
async def history_page(request: Request):
    return templates.TemplateResponse("history.html", {"request": request})
