from fastapi import APIRouter, HTTPException, Depends, status
from app.schemas.trip import (
    Preferences,
    Itinerary,
    # TripGenerateResponse,
    TripSummary,
    # CostBreakdown
)
from app.schemas.user import UserInDB
from app.services.trip import TripService
# from app.services.agent_service import AgentService
from app.dependencies.auth import require_auth
from app.database import get_db
# import os

router = APIRouter()

# Flag to enable/disable agent (useful for testing)
# USE_AGENT = os.getenv("USE_AGENT", "false").lower() == "true"


@router.get("/api/trips", response_model=list[TripSummary])
def list_trips(
    current_user: UserInDB = Depends(require_auth),
    db = Depends(get_db)
):
    """
    List all trips for the authenticated user.

    Returns a list of trip summaries (not full itineraries).
    Requires authentication.
    """
    return TripService.list_trips_for_user(db, current_user.user_id)


# @router.post("/api/trip/generate", response_model=TripGenerateResponse)
# async def generate_trip(preferences: Preferences, db = Depends(get_db)):
#     """
#     Generate a new trip itinerary based on user preferences.
    
#     Returns the itinerary along with cost metadata.
#     Preferences are automatically validated by Pydantic.
#     FastAPI will return 422 with validation errors if invalid.
#     """
#     # Default metadata for mock/fallback
#     metadata = {
#         "total_cost": None,
#         "cost_breakdown": None,
#         "budget_status": "unknown",
#         "over_budget": False
#     }
    
#     # Generate itinerary
#     if USE_AGENT:
#         try:
#             print(f"🤖 Using AI Agent to generate itinerary...")
#             itinerary, metadata = await AgentService.generate_itinerary_from_agent(preferences)
            
#             # Log cost info
#             if metadata.get("total_cost"):
#                 print(f"💰 Total Cost: ${metadata['total_cost']:.2f}")
#                 print(f"📊 Breakdown: {metadata['cost_breakdown']}")
            
#             if metadata.get("over_budget"):
#                 print(f"⚠️  Warning: Trip is over budget by ${metadata['total_cost'] - preferences.budget_limit:.2f}")
                
#         except Exception as e:
#             print(f"❌ Agent failed: {e}. Falling back to mock data.")
#             itinerary = TripService.generate_trip(preferences)
#     else:
#         print(f"📝 Using mock data (set USE_AGENT=true to use AI agent)")
#         itinerary = TripService.generate_trip(preferences)
    
#     # Save to MongoDB
#     TripService.save_itinerary(db, itinerary)
    
#     # Build response with cost metadata
#     cost_breakdown = None
#     if metadata.get("cost_breakdown"):
#         cost_breakdown = CostBreakdown(**metadata["cost_breakdown"])
    
#     return TripGenerateResponse(
#         itinerary=itinerary,
#         total_cost=metadata.get("total_cost"),
#         cost_breakdown=cost_breakdown,
#         budget_status=metadata.get("budget_status", "unknown"),
#         over_budget=metadata.get("over_budget", False)
#     )


@router.get("/api/trip/{trip_id}", response_model=Itinerary)
def get_trip(
    trip_id: str,
    current_user: UserInDB = Depends(require_auth),
    db = Depends(get_db)
):
    """
    Get a specific trip itinerary by ID.

    Requires authentication and verifies ownership.
    """
    itinerary = TripService.get_itinerary(db, trip_id)
    if not itinerary:
        raise HTTPException(status_code=404, detail="Trip not found")

    # Verify ownership
    if itinerary.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this trip"
        )

    return itinerary


@router.put("/api/trip/{trip_id}", response_model=Itinerary)
def update_trip(
    trip_id: str,
    itinerary: Itinerary,
    current_user: UserInDB = Depends(require_auth),
    db = Depends(get_db)
):
    """
    Update an existing trip itinerary.

    Requires authentication and verifies ownership.
    """
    # Get existing trip to verify ownership
    existing_trip = TripService.get_itinerary(db, trip_id)
    if not existing_trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    # Verify ownership
    if existing_trip.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this trip"
        )

    # Update the trip
    success = TripService.update_itinerary(db, trip_id, itinerary)
    if not success:
        raise HTTPException(status_code=404, detail="Trip not found")
    return itinerary


@router.delete("/api/trip/{trip_id}")
def delete_trip(
    trip_id: str,
    current_user: UserInDB = Depends(require_auth),
    db = Depends(get_db)
):
    """
    Delete a trip and all associated discoveries.

    Requires authentication and verifies ownership.
    """
    # Get existing trip to verify ownership
    existing_trip = TripService.get_itinerary(db, trip_id)
    if not existing_trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    # Verify ownership
    if existing_trip.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this trip"
        )

    # Delete the trip
    success = TripService.delete_itinerary(db, trip_id)
    if not success:
        raise HTTPException(status_code=404, detail="Trip not found")
    return {"success": True, "message": "Trip deleted"}


@router.post("/api/trip/{trip_id}/claim", status_code=status.HTTP_200_OK)
def claim_trip(
    trip_id: str,
    current_user: UserInDB = Depends(require_auth),
    db = Depends(get_db)
):
    """
    Claim a guest trip after signup.

    Associates an existing trip (created without auth) with the current user.
    Requires authentication. The trip must not already be owned by another user.
    """
    # Get the trip
    existing_trip = TripService.get_itinerary(db, trip_id)
    if not existing_trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    # Check if trip already has an owner
    if existing_trip.user_id is not None:
        # If it's already owned by this user, just return success
        if existing_trip.user_id == current_user.user_id:
            return {"success": True, "message": "Trip already owned by you"}

        # Otherwise, it belongs to someone else
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Trip is already owned by another user"
        )

    # Claim the trip by setting the user_id
    db.itineraries.update_one(
        {"trip_id": trip_id},
        {"$set": {"user_id": current_user.user_id}}
    )

    return {"success": True, "message": "Trip claimed successfully"}
