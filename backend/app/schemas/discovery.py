from pydantic import BaseModel
from typing import Literal
from datetime import datetime
from enum import Enum

class DiscoveryType(str, Enum):
    """Types of places that can be discovered"""
    RESTAURANT = "restaurant"
    BAR = "bar"
    CAFE = "cafe"
    CLUB = "club"
    SHOPPING = "shopping"
    ATTRACTION = "attraction"

class DiscoveredPlace(BaseModel):
    """Generic place (restaurant, bar, cafe, etc.)"""
    id: str
    place_type: DiscoveryType
    name: str
    address: str
    rating: float
    price_range: str | None = "N/A"  # Allow None from API, default to "N/A"
    google_maps_url: str
    lat: float
    lng: float
    starred: bool = False
    extra_data: dict = {}  # Type-specific fields (e.g., cuisine type, opening hours)

class Discovery(BaseModel):
    """Generic discovery linked to a specific activity"""
    trip_id: str
    activity_id: str
    discovery_type: DiscoveryType
    discovered_at: datetime
    places: list[DiscoveredPlace]

class DiscoveryResponse(BaseModel):
    """Response when fetching discoveries"""
    activity_id: str
    activity_name: str  # Helpful context
    discovery_type: DiscoveryType
    discovered_at: datetime
    places: list[DiscoveredPlace]

class StarPlaceRequest(BaseModel):
    """Request to star/unstar a place"""
    starred: bool

