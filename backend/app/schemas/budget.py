"""
Budget schemas for multi-city budget-aware trip planning.
Defines the data models for budget constraints and results.
"""

from pydantic import BaseModel, Field


class TripBudget(BaseModel):
    """User's budget constraints for multi-city trip planning."""
    origin: str = Field(..., description="IATA code for origin city (e.g., 'NYC', 'MAD')")
    destinations: list[str] = Field(..., description="List of IATA codes for destination cities (e.g., ['ATH', 'ROM', 'PAR'])")
    departure_date: str = Field(..., description="Trip start date in YYYY-MM-DD format")
    return_date: str = Field(..., description="Trip end date in YYYY-MM-DD format")
    adults: int = Field(..., ge=1, le=9, description="Number of adult passengers (1-9)")
    flight_budget: float = Field(..., gt=0, description="Maximum budget for ALL flights (origin->cities->origin) in USD")
    hotel_budget: float = Field(..., gt=0, description="Maximum budget for ALL hotels across all cities in USD")
    activity_budget: float = Field(..., gt=0, description="Maximum budget for activities in USD")
    max_iterations: int = Field(default=5, ge=1, le=10, description="Max replanning attempts if over budget")
    
    class Config:
        json_schema_extra = {
            "example": {
                "origin": "MAD",
                "destinations": ["ATH", "ROM", "PAR"],
                "departure_date": "2026-01-01",
                "return_date": "2026-01-10",
                "adults": 2,
                "flight_budget": 1500.0,
                "hotel_budget": 1200.0,
                "activity_budget": 400.0,
                "max_iterations": 5
            }
        }


class FlightSegment(BaseModel):
    """A single flight leg in the multi-city trip."""
    from_city: str = Field(..., description="Departure city IATA code")
    to_city: str = Field(..., description="Arrival city IATA code")
    date: str | None = Field(None, description="Flight date")
    cost: float = Field(..., description="Flight cost in USD")
    airline: str | None = Field(None, description="Airline name/code")
    is_estimate: bool = Field(default=False, description="True if this is an estimate (e.g., public transport)")


class HotelStay(BaseModel):
    """A hotel stay in one of the destination cities."""
    city: str = Field(..., description="City IATA code")
    nights: int = Field(..., description="Number of nights staying")
    check_in: str | None = Field(None, description="Check-in date")
    check_out: str | None = Field(None, description="Check-out date")
    cost: float = Field(..., description="Total hotel cost in USD")
    hotel_name: str | None = Field(None, description="Hotel name")
    price_per_night: float | None = Field(None, description="Price per night")


class TransportEstimate(BaseModel):
    """Estimated transport cost for nearby cities (train, bus, etc.)."""
    from_city: str = Field(..., description="Departure city")
    to_city: str = Field(..., description="Arrival city")
    transport_type: str = Field(..., description="Type of transport (train, bus, etc.)")
    estimated_cost: float = Field(..., description="Estimated cost in USD")


class BudgetBreakdown(BaseModel):
    """Detailed breakdown of costs vs budgets for multi-city trip."""
    # Per-segment details
    flight_segments: list[FlightSegment] = Field(default_factory=list, description="Cost breakdown per flight leg")
    hotel_stays: list[HotelStay] = Field(default_factory=list, description="Cost breakdown per city hotel")
    transport_estimates: list[TransportEstimate] = Field(default_factory=list, description="Estimated costs for nearby city transport")
    
    # Totals
    flight_cost: float | None = Field(None, description="Total cost of all flights")
    flight_budget: float = Field(..., description="User's flight budget")
    flight_within_budget: bool = Field(..., description="Whether total flight cost is within budget")
    
    hotel_cost: float | None = Field(None, description="Total cost of all hotels")
    hotel_budget: float = Field(..., description="User's hotel budget")
    hotel_within_budget: bool = Field(..., description="Whether total hotel cost is within budget")
    
    activity_cost: float | None = Field(None, description="Estimated activity costs")
    activity_budget: float = Field(..., description="User's activity budget")
    activity_within_budget: bool = Field(..., description="Whether activity cost is within budget")
    
    total_cost: float = Field(..., description="Total cost of flights + hotels + activities")
    total_budget: float = Field(..., description="Total budget (flight + hotel + activity)")
    
    # Trip plan details
    city_order: list[str] = Field(default_factory=list, description="Order of cities visited")
    days_per_city: dict[str, int] = Field(default_factory=dict, description="Number of days allocated per city")


class BudgetResult(BaseModel):
    """Result of multi-city budget-aware trip planning."""
    success: bool = Field(..., description="Whether all costs are within budget")
    message: str = Field(..., description="Summary message of the result")
    iterations_used: int = Field(default=1, description="Number of planning iterations used")
    best_plan_over_budget: float | None = Field(None, description="If failed, how much over budget the best plan is")
    breakdown: BudgetBreakdown | None = Field(None, description="Detailed cost breakdown")
    budget_errors: list[str] = Field(default_factory=list, description="List of budget constraint violations")
    agent_reasoning: str | None = Field(None, description="The agent's reasoning and final response")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Found plan within budget after 2 iterations",
                "iterations_used": 2,
                "best_plan_over_budget": None,
                "breakdown": {
                    "flight_segments": [
                        {"from_city": "MAD", "to_city": "ROM", "cost": 180.0, "is_estimate": False},
                        {"from_city": "ROM", "to_city": "ATH", "cost": 120.0, "is_estimate": False},
                        {"from_city": "ATH", "to_city": "PAR", "cost": 250.0, "is_estimate": False},
                        {"from_city": "PAR", "to_city": "MAD", "cost": 150.0, "is_estimate": False}
                    ],
                    "hotel_stays": [
                        {"city": "ROM", "nights": 3, "cost": 350.0},
                        {"city": "ATH", "nights": 3, "cost": 280.0},
                        {"city": "PAR", "nights": 3, "cost": 420.0}
                    ],
                    "flight_cost": 700.0,
                    "flight_budget": 1500.0,
                    "flight_within_budget": True,
                    "hotel_cost": 1050.0,
                    "hotel_budget": 1200.0,
                    "hotel_within_budget": True,
                    "activity_cost": 0.0,
                    "activity_budget": 400.0,
                    "activity_within_budget": True,
                    "total_cost": 1750.0,
                    "total_budget": 3100.0,
                    "city_order": ["ROM", "ATH", "PAR"],
                    "days_per_city": {"ROM": 3, "ATH": 3, "PAR": 3}
                },
                "budget_errors": []
            }
        }
