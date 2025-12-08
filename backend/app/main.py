from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import trip, user, discovery, session
from app.database import initialize_indexes
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

app = FastAPI(
    title="Coastline API",
    description="AI Travel Planner with Smart Discovery",
    version="0.1.0"
)

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update with specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(trip.router, tags=["trips"])
app.include_router(discovery.router, tags=["discovery"])
app.include_router(user.router, tags=["users"])
app.include_router(session.router, tags=["sessions"])

@app.on_event("startup")
def startup_event():
    """Initialize database indexes on startup"""
    initialize_indexes()

@app.get("/")
def read_root():
    backend_port = os.getenv("BACKEND_PORT", "8008")
    return {
        "message": "Coastline API - AI Travel Planner",
        "version": "0.1.0",
        "docs": "/docs",
        "run_hint": f"To run on port {backend_port}, start with: uvicorn app.main:app --reload --port {backend_port}"
    }

# Hint: Run your server with:
# uvicorn app.main:app --reload --port ${BACKEND_PORT:-8008}
# Or set BACKEND_PORT environment variable (defaults to 8008)