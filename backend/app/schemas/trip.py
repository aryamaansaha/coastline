from pydantic import BaseModel, field_validator, model_validator
from typing import Literal
from datetime import datetime, timezone

# Preferences we obtain from the initial user input 
class Preferences(BaseModel):
    destinations: list[str]  # Can be multiple cities: ["London", "Paris", "Amsterdam"]
    start_date: datetime
    end_date: datetime
    budget_limit: float
    origin: str | None = None  # Starting location (e.g., "New York")
    # ... other preferences like food preferences, activity preferences, etc.
    
    @field_validator('destinations')
    @classmethod
    def validate_destinations(cls, v):
        if not v or len(v) == 0:
            raise ValueError('At least one destination is required')
        return v
    
    @field_validator('budget_limit')
    @classmethod
    def validate_budget(cls, v):
        if v <= 0:
            raise ValueError('Budget must be positive')
        return v
    
    @field_validator('start_date')
    @classmethod
    def validate_start_date(cls, v):
        # Normalize to timezone-aware (UTC)
        if v.tzinfo is None:
            v_aware = v.replace(tzinfo=timezone.utc)
        else:
            v_aware = v
        
        # Validate it's in the future
        now = datetime.now(timezone.utc)
        if v_aware < now:
            raise ValueError('Start date must be in the future')
        
        # Return normalized value to ensure consistency
        return v_aware
    
    @field_validator('end_date')
    @classmethod
    def validate_end_date(cls, v):
        # Normalize to timezone-aware (UTC) for consistency with start_date
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v
    
    @model_validator(mode='after')
    def validate_date_range(self):
        # Both dates are now guaranteed to be timezone-aware
        if self.start_date >= self.end_date:
            raise ValueError('End date must be after start date')
        return self

# Location we obtain from the LLM (as part of the ItineraryLLMCreate output itself)
class LocationLLMCreate(BaseModel):
    name: str
    address: str

# Final Location after we obtain the lat and lng from the Open Source maps API
class Location(LocationLLMCreate):
    lat: float | None
    lng: float | None

# Activity we obtain from the LLM (as part of the ItineraryLLMCreate output itself)
class ActivityLLMCreate(BaseModel):
    type: Literal["flight", "hotel", "activity"]
    time_slot: str
    title: str
    description: str
    activity_suggestion: str
    location: LocationLLMCreate
    estimated_cost: float
    price_suggestion: str
    currency: str

# Final Activity object; part of the Itinerary object we want to persist
class Activity(ActivityLLMCreate):
    id: str
    location: Location
    # time_slot inherited from ActivityLLMCreate as str (e.g., "08:31 AM")

# Day we obtain from the LLM (as part of the ItineraryLLMCreate output itself)
class DayLLMCreate(BaseModel):
    day_number: int
    theme: str
    city: str  # Which city this day takes place in (for multi-city trips)
    activities: list[ActivityLLMCreate]

# Final Day object; part of the Itinerary object we want to persist
class Day(DayLLMCreate):
    id: str
    activities: list[Activity]

# LLM generates this object, we hope to validate it against the ItineraryLLMCreate schema
class ItineraryLLMCreate(BaseModel):
    trip_title: str
    days: list[DayLLMCreate]

# Final Itinerary object; part of the Itinerary object we want to persist
class Itinerary(ItineraryLLMCreate):
    trip_id: str
    days: list[Day]
    budget_limit: float


# ============================================================================
# API RESPONSE SCHEMAS
# ============================================================================

class CostBreakdown(BaseModel):
    """Cost breakdown by category"""
    flights: float = 0.0
    hotels: float = 0.0
    activities: float = 0.0


class TripGenerateResponse(BaseModel):
    """Response from trip generation endpoint"""
    itinerary: Itinerary
    total_cost: float | None
    cost_breakdown: CostBreakdown | None
    budget_status: str  # "under", "over", "unknown"
    over_budget: bool


class TripSummary(BaseModel):
    """Summary of a trip for listing endpoints"""
    trip_id: str
    trip_title: str
    budget_limit: float
    destinations: list[str]  # Extracted from days
    num_days: int
    created_at: datetime | None = None
    updated_at: datetime | None = None