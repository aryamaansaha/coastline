from fastapi import APIRouter, HTTPException, Depends
from app.schemas.trip import Preferences, Itinerary
from app.services.trip import TripService
from app.services.agent_service import AgentService
from app.database import get_db
import os

router = APIRouter()

# Flag to enable/disable agent (useful for testing)
USE_AGENT = os.getenv("USE_AGENT", "false").lower() == "true"

@router.post("/api/trip/generate", response_model=Itinerary)
async def generate_trip(preferences: Preferences, db = Depends(get_db)):
    """
    Generate a new trip itinerary based on user preferences.
    
    Preferences are automatically validated by Pydantic.
    FastAPI will return 422 with validation errors if invalid.
    """
    # Generate itinerary
    if USE_AGENT:
        try:
            print(f"🤖 Using AI Agent to generate itinerary...")
            itinerary, metadata = await AgentService.generate_itinerary_from_agent(preferences)
            
            # Log cost info
            print(f"💰 Total Cost: ${metadata['total_cost']:.2f}")
            print(f"📊 Breakdown: {metadata['cost_breakdown']}")
            
            if metadata.get("over_budget"):
                print(f"⚠️  Warning: Trip is over budget by ${metadata['total_cost'] - preferences.budget_limit:.2f}")
                
        except Exception as e:
            print(f"❌ Agent failed: {e}. Falling back to mock data.")
            itinerary = TripService.generate_trip(preferences)
    else:
        print(f"📝 Using mock data (set USE_AGENT=true to use AI agent)")
        itinerary = TripService.generate_trip(preferences)
    
    # Save to MongoDB
    TripService.save_itinerary(db, itinerary)
    
    return itinerary


@router.get("/api/trip/{trip_id}", response_model=Itinerary)
def get_trip(trip_id: str, db = Depends(get_db)):
    """Get a specific trip itinerary by ID"""
    itinerary = TripService.get_itinerary(db, trip_id)
    if not itinerary:
        raise HTTPException(status_code=404, detail="Trip not found")
    return itinerary


@router.put("/api/trip/{trip_id}", response_model=Itinerary)
def update_trip(trip_id: str, itinerary: Itinerary, db = Depends(get_db)):
    """Update an existing trip itinerary"""
    success = TripService.update_itinerary(db, trip_id, itinerary)
    if not success:
        raise HTTPException(status_code=404, detail="Trip not found")
    return itinerary


@router.delete("/api/trip/{trip_id}")
def delete_trip(trip_id: str, db = Depends(get_db)):
    """Delete a trip and all associated discoveries"""
    success = TripService.delete_itinerary(db, trip_id)
    if not success:
        raise HTTPException(status_code=404, detail="Trip not found")
    return {"success": True, "message": "Trip deleted"}
