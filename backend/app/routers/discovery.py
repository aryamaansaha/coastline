from fastapi import APIRouter, HTTPException, Depends, Query
from app.schemas.discovery import (
    Discovery,
    DiscoveredPlace,
    DiscoveryResponse,
    DiscoveryType,
    StarPlaceRequest
)
from app.services.discovery import DiscoveryService
from app.services.trip import TripService
from app.database import get_db
from datetime import datetime

router = APIRouter()

@router.post(
    "/api/trip/{trip_id}/activities/{activity_id}/discover/{place_type}",
    response_model=list[DiscoveredPlace],
    summary="Discover places near an activity",
    description="""
    Discover places (restaurants, bars, cafes, etc.) near a specific activity.
    
    - First call: Discovers and caches places
    - Subsequent calls: Returns cached places
    - regenerate=true: Keeps starred places, fetches new ones
    """
)
def discover_places(
    trip_id: str,
    activity_id: str,
    place_type: DiscoveryType,
    regenerate: bool = Query(False, description="Regenerate places, keeping starred ones"),
    db = Depends(get_db)
):
    """
    Discover places near an activity.
    
    Examples:
    - POST /api/trip/{id}/activities/{id}/discover/restaurant
    - POST /api/trip/{id}/activities/{id}/discover/bar?regenerate=true
    """
    
    # Check if activity exists
    activity = TripService.get_activity(db, trip_id, activity_id)
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    if not activity.location.lat or not activity.location.lng:
        raise HTTPException(
            status_code=400, 
            detail="Activity location missing coordinates. Please geocode first."
        )
    
    # Check for existing discovery
    existing = DiscoveryService.get_discovery(db, trip_id, activity_id, place_type)
    
    if existing and not regenerate:
        # Return cached places
        return existing.places
    
    # Determine action: regenerate or first-time discovery
    if regenerate and existing:
        # Regenerate keeping starred
        places = DiscoveryService.regenerate_places(
            db, trip_id, activity_id, place_type,
            activity.location.lat, activity.location.lng
        )
    else:
        # First time discovery
        places = DiscoveryService.discover_places(
            db, trip_id, activity_id, place_type,
            activity.location.lat, activity.location.lng
        )
    
    # Save discovery
    
    discovery = Discovery(
        trip_id=trip_id,
        activity_id=activity_id,
        discovery_type=place_type,
        discovered_at=datetime.now(),
        places=places
    )
    DiscoveryService.save_discovery(db, discovery)
    
    return places


@router.put(
    "/api/trip/{trip_id}/activities/{activity_id}/discover/{place_type}/{place_id}/star",
    summary="Star or unstar a place",
    description="Mark a place as a favorite (starred) or remove the star"
)
def star_place(
    trip_id: str,
    activity_id: str,
    place_type: DiscoveryType,
    place_id: str,
    request: StarPlaceRequest,
    db = Depends(get_db)
):
    """Star or unstar a discovered place"""
    
    # Verify discovery exists
    discovery = DiscoveryService.get_discovery(db, trip_id, activity_id, place_type)
    if not discovery:
        raise HTTPException(status_code=404, detail="Discovery not found")
    
    # Verify place exists in discovery
    place_exists = any(p.id == place_id for p in discovery.places)
    if not place_exists:
        raise HTTPException(status_code=404, detail="Place not found in discovery")
    
    # Update starred status
    DiscoveryService.star_place(
        db, trip_id, activity_id, place_type, place_id, request.starred
    )
    
    return {"success": True, "starred": request.starred}


@router.get(
    "/api/trip/{trip_id}/discoveries",
    response_model=list[DiscoveryResponse],
    summary="Get all discoveries for a trip",
    description="Retrieve all discovered places (all types) for a trip"
)
def get_all_discoveries(
    trip_id: str,
    place_type: DiscoveryType | None = Query(None, description="Filter by place type"),
    db = Depends(get_db)
):
    """Get all discoveries for a trip, optionally filtered by place type"""
    
    # Get itinerary to enrich responses with activity names
    itinerary = TripService.get_itinerary(db, trip_id)
    if not itinerary:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    # Build activity map
    activity_map = {}
    for day in itinerary.days:
        for activity in day.activities:
            activity_map[activity.id] = activity.title
    
    # Get discoveries
    if place_type:
        discoveries = DiscoveryService.get_discoveries_by_type(db, trip_id, place_type)
    else:
        discoveries = DiscoveryService.get_all_discoveries_for_trip(db, trip_id)
    
    # Build response with activity names
    response = []
    for discovery in discoveries:
        response.append(DiscoveryResponse(
            activity_id=discovery.activity_id,
            activity_name=activity_map.get(discovery.activity_id, "Unknown Activity"),
            discovery_type=discovery.discovery_type,
            discovered_at=discovery.discovered_at,
            places=discovery.places
        ))
    
    return response


@router.delete(
    "/api/trip/{trip_id}/activities/{activity_id}/discover/{place_type}",
    summary="Delete a discovery",
    description="Remove all discovered places for an activity (useful for full reset)"
)
def delete_discovery(
    trip_id: str,
    activity_id: str,
    place_type: DiscoveryType,
    db = Depends(get_db)
):
    """Delete a discovery (clears all places for an activity/type)"""
    
    result = db.discoveries.delete_one({
        "trip_id": trip_id,
        "activity_id": activity_id,
        "discovery_type": place_type.value
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Discovery not found")
    
    return {"success": True, "message": "Discovery deleted"}

