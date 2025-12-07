from pydantic import BaseModel, field_validator
from typing import Literal, Optional
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


# ============================================================================
# LLM OUTPUT VALIDATION SCHEMA
# ============================================================================

class PlaceLLMCreate(BaseModel):
    """
    Schema for validating Gemini LLM output for discovered places.
    Works for all place types (restaurants, bars, cafes, clubs, etc.)
    since they all share the same JSON structure.
    """
    name: str
    address: str
    rating: Optional[float] = None  # Can be None if not available
    price_range: Optional[str] = None  # Can be None if not available
    google_maps_url: str
    
    @field_validator('rating', mode='before')
    @classmethod
    def validate_rating(cls, v):
        """Handle missing/invalid ratings gracefully"""
        if v is None:
            return None
        try:
            rating = float(v)
            # Clamp to valid range instead of failing
            if rating < 0:
                return 0.0
            if rating > 5:
                return 5.0
            return rating
        except (ValueError, TypeError):
            return None  # Return None for invalid ratings
    
    @field_validator('google_maps_url')
    @classmethod
    def validate_url(cls, v):
        """Basic URL validation"""
        if not v:
            raise ValueError('Google Maps URL is required')
        if not isinstance(v, str):
            raise ValueError('Google Maps URL must be a string')
        # Accept any URL-like string (Gemini sometimes returns different formats)
        if not ('http' in v.lower() or 'maps.google' in v.lower() or 'goo.gl' in v.lower()):
            raise ValueError(f'Invalid Google Maps URL format: {v}')
        return v
    
    @field_validator('name', 'address')
    @classmethod
    def validate_not_empty(cls, v, info):
        """Ensure name and address are not empty"""
        if not v or not v.strip():
            raise ValueError(f'{info.field_name} cannot be empty')
        return v.strip()


# ============================================================================
# DATABASE/API SCHEMAS
# ============================================================================

class DiscoveredPlace(BaseModel):
    """Generic place (restaurant, bar, cafe, etc.) stored in DB"""
    id: str
    place_type: DiscoveryType
    name: str
    address: str
    rating: float | None = None  # Allow None if rating unavailable
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

