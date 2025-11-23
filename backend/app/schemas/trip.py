from pydantic import BaseModel
from typing import Literal
from datetime import datetime

class Preferences(BaseModel):
    destinations: list[str]
    start_date: datetime
    end_date: datetime
    budget: float

class LocationLLMCreate(BaseModel):
    name: str
    address: str

class Location(LocationLLMCreate):
    lat: float | None
    lng: float | None

class ActivityLLMCreate(BaseModel):
    type: Literal["flight", "hotel", "food", "activity"]
    time_slot: str
    title: str
    description: str
    activity_suggestion: str
    location: LocationLLMCreate
    estimated_cost: float
    price_suggestion: str
    currency: str

class Activity(ActivityLLMCreate):
    id: str
    location: Location
    time_slot: datetime

class DayLLMCreate(BaseModel):
    day_number: int
    theme: str
    activities: list[ActivityLLMCreate]

class Day(DayLLMCreate):
    id: str
    activities: list[Activity]

class ItineraryLLMCreate(BaseModel):
    trip_title: str
    total_budget_limit: float
    days: list[DayLLMCreate]

class Itinerary(ItineraryLLMCreate):
    id: str
    days: list[Day]