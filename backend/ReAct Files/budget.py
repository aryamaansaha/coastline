"""
Multi-city budget-aware trip planning API endpoints.
Uses ReAct agent to search flights/hotels across multiple cities
and iteratively replans to meet budget constraints.
"""

import asyncio
from fastapi import APIRouter, HTTPException
from app.schemas.budget import TripBudget, BudgetResult
from app.services.budget_agent import BudgetAgentService

router = APIRouter()


@router.post("/api/trip/generate-with-budget", response_model=BudgetResult)
def generate_trip_with_budget(budget: TripBudget) -> BudgetResult:
    """
    Generate a multi-city trip itinerary within specified budget constraints.
    
    This endpoint:
    1. Takes user's origin, list of destination cities, dates, and 3 separate budgets
    2. Uses a ReAct agent with MCP to search real flight/hotel prices for ALL cities
    3. The agent decides:
       - Order of cities to visit
       - Number of days per city
       - Flights between all cities (or public transport for nearby cities)
       - Hotels for each city
    4. If over budget, automatically replans with different arrangements
    5. Iterates up to max_iterations times to find a plan within budget
    6. Returns best plan found, even if over budget (with recommendation)
    
    Args:
        budget: TripBudget with:
            - origin: Starting city (e.g., "MAD")
            - destinations: List of cities to visit (e.g., ["ATH", "ROM", "PAR"])
            - departure_date: Trip start date
            - return_date: Trip end date
            - adults: Number of passengers
            - flight_budget: Budget for ALL flights (origin->cities->origin)
            - hotel_budget: Budget for ALL hotels across all cities
            - activity_budget: Budget for activities
            - max_iterations: Max replanning attempts (default: 5)
        
    Returns:
        BudgetResult with:
        - success: Whether all budgets were met
        - message: Summary (or how much over budget)
        - iterations_used: How many planning attempts were made
        - best_plan_over_budget: If failed, how much the best plan exceeded budget
        - breakdown: Detailed per-segment costs (flight_segments, hotel_stays, etc.)
        - budget_errors: List of specific budget violations
        - agent_reasoning: The agent's full response
    
    Example request:
        POST /api/trip/generate-with-budget
        {
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
    
    Example success response:
        {
            "success": true,
            "message": "Success! Found plan within budget after 2 iteration(s).",
            "iterations_used": 2,
            "breakdown": {
                "flight_segments": [
                    {"from_city": "MAD", "to_city": "ROM", "cost": 180.0},
                    {"from_city": "ROM", "to_city": "ATH", "cost": 120.0},
                    ...
                ],
                "hotel_stays": [
                    {"city": "ROM", "nights": 3, "cost": 350.0},
                    ...
                ],
                "city_order": ["ROM", "ATH", "PAR"],
                "days_per_city": {"ROM": 3, "ATH": 3, "PAR": 3}
            }
        }
    
    Example failure response:
        {
            "success": false,
            "message": "Could not meet budget after 5 iterations. Best plan is $247.50 over budget.",
            "iterations_used": 5,
            "best_plan_over_budget": 247.50,
            ...
        }
    """
    try:
        result = asyncio.run(BudgetAgentService.plan_trip_with_budget(budget))
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error planning multi-city trip: {str(e)}"
        )



#this literally does the same thing as generate trip with budget, so should probably delete. 

#cursos gerneated this as an endpoint so that it has a different name, so i'll keep it for now sicne this 
# could be modified to be a lightweight budget validation, but should delete imo
@router.post("/api/trip/validate-budget", response_model=BudgetResult)
def validate_budget(budget: TripBudget) -> BudgetResult:
    """
    Validate if a budget is realistic for the given multi-city route.
    
    Same as generate-with-budget but named for clarity when just checking feasibility.
    Useful to quickly check if a trip is affordable before committing.
    
    Args:
        budget: TripBudget with trip details and budget constraints
        
    Returns:
        BudgetResult indicating whether the trip is feasible within budget
    """
    try:
        result = asyncio.run(BudgetAgentService.plan_trip_with_budget(budget))
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error validating budget: {str(e)}"
        )
