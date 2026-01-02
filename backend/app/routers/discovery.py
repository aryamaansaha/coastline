from fastapi import APIRouter, HTTPException, Depends, Query, status
from app.schemas.discovery import (
    Discovery,
    DiscoveredPlace,
    DiscoveryResponse,
    DiscoveryType,
    StarPlaceRequest
)
from app.schemas.user import UserInDB
from app.services.discovery import DiscoveryService
from app.services.trip import TripService
from app.dependencies.auth import require_auth, get_current_user
from app.database import get_db
from datetime import datetime

router = APIRouter()


def _verify_trip_access(db, trip_id: str, user_id: str | None):
    """
    Verify that the user can access this trip.
    - Authenticated users: Must own the trip
    - Guest users: Can only access guest trips (user_id = None)

    Raises HTTPException if not found or not authorized.
    Returns the trip if access is granted.
    """
    trip = TripService.get_itinerary(db, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    # Guest trying to access a trip
    if user_id is None:
        # Guests can only access guest trips
        if trip.user_id is not None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required to access this trip"
            )
    else:
        # Authenticated user trying to access a trip
        if trip.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this trip"
            )

    return trip


def _check_guest_discovery_limit(db, trip_id: str):
    """
    Check if a guest trip has reached the discovery limit (3 discoveries).
    Raises HTTPException if limit is reached.
    """
    GUEST_DISCOVERY_LIMIT = 3

    # Count existing discoveries for this trip
    discovery_count = db.discoveries.count_documents({"trip_id": trip_id})

    if discovery_count >= GUEST_DISCOVERY_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Guest users are limited to {GUEST_DISCOVERY_LIMIT} discoveries per trip. Please sign up to continue exploring!"
        )


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
    current_user: UserInDB | None = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Discover places near an activity.

    Supports GUEST FLOW: Authentication is optional.
    - Guest users: Limited to 3 discoveries per trip
    - Authenticated users: Unlimited discoveries

    Examples:
    - POST /api/trip/{id}/activities/{id}/discover/restaurant
    - POST /api/trip/{id}/activities/{id}/discover/bar?regenerate=true
    """

    user_id = current_user.user_id if current_user else None

    # Verify trip access (guests can access guest trips, users can access their trips)
    trip = _verify_trip_access(db, trip_id, user_id)

    # Check discovery limit for guest trips
    if trip.user_id is None:
        _check_guest_discovery_limit(db, trip_id)

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
    current_user: UserInDB | None = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Star or unstar a discovered place.

    Supports GUEST FLOW: Authentication is optional.
    Guests can star places in their guest trips.
    """

    user_id = current_user.user_id if current_user else None

    # Verify trip access
    _verify_trip_access(db, trip_id, user_id)

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
    current_user: UserInDB | None = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Get all discoveries for a trip, optionally filtered by place type.

    Supports GUEST FLOW: Authentication is optional.
    Guests can view discoveries for their guest trips.
    """

    user_id = current_user.user_id if current_user else None

    # Verify trip access and get itinerary
    itinerary = _verify_trip_access(db, trip_id, user_id)
    
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
    current_user: UserInDB | None = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Delete a discovery (clears all places for an activity/type).

    Supports GUEST FLOW: Authentication is optional.
    Guests can delete discoveries from their guest trips.
    """

    user_id = current_user.user_id if current_user else None

    # Verify trip access
    _verify_trip_access(db, trip_id, user_id)

    result = db.discoveries.delete_one({
        "trip_id": trip_id,
        "activity_id": activity_id,
        "discovery_type": place_type.value
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Discovery not found")
    
    return {"success": True, "message": "Discovery deleted"}

