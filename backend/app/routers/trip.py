from fastapi import APIRouter
from app.schemas.trip import Preferences, Itinerary
router = APIRouter()

@router.post("api/trip/generate")
def generate_trip(preferences: Preferences):
    # LLM agent will return an itinerary
    # could also pass a summary of preferences instead of a JSON, gotta discuss
    return {"message": "Trip generated successfully"}


@router.get("api/trip/{trip_id}")
def get_trip(trip_id: str) -> Itinerary:
    # get the itinerary from the database
    return {"message": "Trip retrieved successfully"}
