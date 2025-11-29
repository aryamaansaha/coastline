from fastapi import APIRouter
from app.schemas.trip import Preferences, Itinerary
from app.services.trip import TripService

router = APIRouter()

@router.post("/api/trip/generate", response_model=Itinerary)
def generate_trip(preferences: Preferences):
    """Generate a trip itinerary based on user preferences"""
    # LLM agent will return an itinerary (using mock data for now)
    itinerary = TripService.generate_trip(preferences)
    # TODO: Save to MongoDB once connected
    return itinerary


@router.get("/api/trip/{trip_id}", response_model=Itinerary)
def get_trip(trip_id: str):
    """Get a specific trip itinerary by ID"""
    # TODO: Retrieve from MongoDB
    # For now, return mock data
    from datetime import datetime
    mock_preferences = Preferences(
        destinations=["Paris"],
        start_date=datetime(2024, 6, 1),
        end_date=datetime(2024, 6, 3),
        budget_limit=500.0
    )
    return TripService.generate_trip(mock_preferences)
