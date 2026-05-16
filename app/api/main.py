"""
Secure RAG MVP — FastAPI Application
Main entry point with health check, CORS, and route registration.
"""

import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.api.routes_ingest import router as ingest_router
from app.api.routes_query import router as query_router


# Track startup time for health check
_start_time: float = 0.0


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle — startup and shutdown hooks."""
    global _start_time
    _start_time = time.time()

    settings = get_settings()
    print(f"🚀 Secure RAG MVP starting...")
    print(f"   Environment:  {settings.app_env}")
    print(f"   LLM Model:    {settings.llm_model}")
    print(f"   Embed Model:  {settings.embedding_model}")
    print(f"   Ollama Host:  {settings.ollama_host}")
    print(f"   Context:      {settings.llm_context_window} tokens")
    print(f"   GPU:          NVIDIA RTX 3050 (CUDA)")

    yield

    print("👋 Secure RAG MVP shutting down...")


app = FastAPI(
    title="Secure RAG MVP",
    description=(
        "A defense-in-depth, fully local RAG system with trusted/quarantine "
        "separation, output firewall, and built-in red-team evaluation."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# --- CORS (permissive for local dev, tighten in production) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Register routers ---
app.include_router(ingest_router, prefix="/api/v1", tags=["Ingestion"])
app.include_router(query_router, prefix="/api/v1", tags=["Query"])

# --- Serve dashboard (if directory exists) ---
_dashboard_dir = Path(__file__).parent.parent.parent / "dashboard"
if _dashboard_dir.exists():
    app.mount("/dashboard", StaticFiles(directory=str(_dashboard_dir), html=True), name="dashboard")


# --- Health Check ---
@app.get("/health", tags=["System"])
async def health_check():
    """
    System health check endpoint.
    Returns service status and configuration summary.
    """
    settings = get_settings()
    uptime = time.time() - _start_time if _start_time else 0

    return {
        "status": "healthy",
        "version": "0.1.0",
        "uptime_seconds": round(uptime, 2),
        "config": {
            "llm_model": settings.llm_model,
            "embedding_model": settings.embedding_model,
            "ollama_host": settings.ollama_host,
            "context_window": settings.llm_context_window,
            "trust_threshold": settings.trust_threshold,
            "environment": settings.app_env,
        },
    }


@app.get("/", tags=["System"])
async def root():
    """Root endpoint — redirects to docs."""
    return {
        "message": "Secure RAG MVP API",
        "docs": "/docs",
        "health": "/health",
    }
