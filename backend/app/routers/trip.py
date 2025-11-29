from fastapi import APIRouter, HTTPException, Depends
from app.schemas.trip import Preferences, Itinerary
from app.services.trip import TripService
from app.database import get_db

router = APIRouter()

@router.post("/api/trip/generate", response_model=Itinerary)
def generate_trip(preferences: Preferences, db = Depends(get_db)):
    """Generate a new trip itinerary based on user preferences"""
    # Generate itinerary (mock for now, agent later)
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
