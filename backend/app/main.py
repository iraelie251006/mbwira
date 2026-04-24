"""Mbwira — FastAPI entry point."""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings
from app.models.db import init_db
from app.routers import ussd, chat, whatsapp, counselor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger("mbwira")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Mbwira (env=%s)", settings.app_env)
    await init_db()
    yield
    logger.info("Shutting down")


app = FastAPI(
    title="Mbwira",
    description="Kinyarwanda SRH + mental health companion for Rwandan youth",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ussd.router)
app.include_router(chat.router)
app.include_router(whatsapp.router)
app.include_router(counselor.router)


# ---- Static frontend ----
FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/")
    async def index():
        return FileResponse(FRONTEND_DIR / "index.html")

    @app.get("/chat-ui")
    async def chat_ui():
        return FileResponse(FRONTEND_DIR / "chat.html")

    @app.get("/dashboard")
    async def dashboard():
        return FileResponse(FRONTEND_DIR / "counselor.html")

    @app.get("/ussd-sim")
    async def ussd_sim():
        return FileResponse(FRONTEND_DIR / "ussd_simulator.html")


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "service": "mbwira"}
