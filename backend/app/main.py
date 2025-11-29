from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import localizer, trip, user, discovery
from app.database import initialize_indexes
import os

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
app.include_router(localizer.router, tags=["localizer"])
app.include_router(user.router, tags=["users"])

@app.on_event("startup")
def startup_event():
    """Initialize database indexes on startup"""
    initialize_indexes()

@app.get("/")
def read_root():
    return {
        "message": "Coastline API - AI Travel Planner",
        "version": "0.1.0",
        "docs": "/docs",
        "run_hint": "To run on port 8008, start with: uvicorn app.main:app --reload --port 8008"
    }

# Hint: Run your server on port 8008 with:
# uvicorn app.main:app --reload --port 8008