from pymongo import MongoClient, ASCENDING
from functools import lru_cache
import os

@lru_cache()
def get_mongo_client():
    """
    Get MongoDB client (singleton pattern via lru_cache).
    
    The client is created once and reused across all requests.
    MongoClient internally manages a connection pool for efficient concurrent access.
    """
    mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
    return MongoClient(mongo_uri)

def get_db():
    """
    FastAPI dependency for getting database instance.
    
    Usage:
        @router.get("/some-route")
        def handler(db = Depends(get_db)):
            db.collection.find_one(...)
    """
    client = get_mongo_client()
    db = client.coastline  # Database name
    return db

def initialize_indexes():
    """
    Create MongoDB indexes for optimal query performance.
    Should be called once on application startup.
    """
    db = get_db()
    
    # Itineraries collection
    db.itineraries.create_index([("trip_id", ASCENDING)], unique=True)
    db.itineraries.create_index([("created_at", ASCENDING)])
    
    # Discoveries collection
    # Compound index for efficient lookups by trip + activity + type
    db.discoveries.create_index([
        ("trip_id", ASCENDING),
        ("activity_id", ASCENDING),
        ("discovery_type", ASCENDING)
    ], unique=True)
    
    # Index for querying all discoveries for a trip
    db.discoveries.create_index([("trip_id", ASCENDING)])
    
    # Sessions collection (for HITL workflow)
    db.sessions.create_index([("session_id", ASCENDING)], unique=True)
    db.sessions.create_index([("expires_at", ASCENDING)])  # For TTL cleanup
    db.sessions.create_index([("status", ASCENDING)])
    db.sessions.create_index([("created_at", ASCENDING)])
    
    # Agent checkpoints collection (for LangGraph state persistence)
    db.agent_checkpoints.create_index([
        ("thread_id", ASCENDING),
        ("checkpoint_id", ASCENDING),
        ("checkpoint_ns", ASCENDING)
    ], unique=True)
    db.agent_checkpoints.create_index([("thread_id", ASCENDING)])
    
    print("✅ MongoDB indexes initialized")

