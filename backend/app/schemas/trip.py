from pydantic import BaseModel, field_validator, model_validator
from typing import Literal
from datetime import datetime

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
        if v < datetime.now():
            raise ValueError('Start date must be in the future')
        return v
    
    @model_validator(mode='after')
    def validate_date_range(self):
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
    time_slot: datetime

# Day we obtain from the LLM (as part of the ItineraryLLMCreate output itself)
class DayLLMCreate(BaseModel):
    day_number: int
    theme: str
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