"""
Multi-city budget-aware travel agent service.
Uses OpenAI + MCP to search flights/hotels across multiple cities
and iteratively replans to meet budget constraints.
"""

import sys
import json
import asyncio
from pathlib import Path
from typing import Any
from openai import AsyncOpenAI
from app.schemas.budget import (
    TripBudget, BudgetResult, BudgetBreakdown,
    FlightSegment, HotelStay, TransportEstimate
)


class BudgetAgentService:
    """Service for multi-city budget-aware trip planning."""
    
    @staticmethod
    def build_breakdown_from_parsed_data(
        budget: TripBudget,
        flight_segments: list[FlightSegment],
        hotel_stays: list[HotelStay],
        transport_estimates: list[TransportEstimate],
        city_order: list[str],
        days_per_city: dict[str, int]
    ) -> BudgetBreakdown:
        """Build a BudgetBreakdown from parsed agent data."""
        
        # Calculate totals
        flight_cost = sum(seg.cost for seg in flight_segments)
        transport_cost = sum(est.estimated_cost for est in transport_estimates)
        total_flight_cost = flight_cost + transport_cost
        
        hotel_cost = sum(stay.cost for stay in hotel_stays)
        activity_cost = 0.0  # Placeholder
        
        total_cost = total_flight_cost + hotel_cost + activity_cost
        total_budget = budget.flight_budget + budget.hotel_budget + budget.activity_budget
        
        return BudgetBreakdown(
            flight_segments=flight_segments,
            hotel_stays=hotel_stays,
            transport_estimates=transport_estimates,
            flight_cost=total_flight_cost,
            flight_budget=budget.flight_budget,
            flight_within_budget=total_flight_cost <= budget.flight_budget,
            hotel_cost=hotel_cost,
            hotel_budget=budget.hotel_budget,
            hotel_within_budget=hotel_cost <= budget.hotel_budget,
            activity_cost=activity_cost,
            activity_budget=budget.activity_budget,
            activity_within_budget=activity_cost <= budget.activity_budget,
            total_cost=total_cost,
            total_budget=total_budget,
            city_order=city_order,
            days_per_city=days_per_city
        )
    
    @staticmethod
    def check_budget_constraints(breakdown: BudgetBreakdown) -> tuple[bool, list[str]]:
        """
        Check if the breakdown meets all budget constraints.
        
        Returns:
            Tuple of (all_within_budget, error_messages)
        """
        errors = []
        
        # Check flight budget
        if breakdown.flight_cost is not None:
            if not breakdown.flight_within_budget:
                over_by = breakdown.flight_cost - breakdown.flight_budget
                errors.append(
                    f"Flight budget exceeded by ${over_by:.2f}: "
                    f"Total flights cost ${breakdown.flight_cost:.2f}, "
                    f"but budget is ${breakdown.flight_budget:.2f}."
                )
        else:
            errors.append("Could not determine flight costs.")
        
        # Check hotel budget
        if breakdown.hotel_cost is not None:
            if not breakdown.hotel_within_budget:
                over_by = breakdown.hotel_cost - breakdown.hotel_budget
                errors.append(
                    f"Hotel budget exceeded by ${over_by:.2f}: "
                    f"Total hotels cost ${breakdown.hotel_cost:.2f}, "
                    f"but budget is ${breakdown.hotel_budget:.2f}."
                )
        else:
            errors.append("Could not determine hotel costs.")
        
        all_within_budget = (
            breakdown.flight_within_budget and 
            breakdown.hotel_within_budget and 
            breakdown.activity_within_budget
        )
        
        return all_within_budget, errors
    
    @staticmethod
    def parse_tool_results(tool_results: list[dict], budget: TripBudget) -> tuple[
        list[FlightSegment], list[HotelStay], list[TransportEstimate], list[str], dict[str, int]
    ]:
        """
        Extract flight segments, hotel stays from tool call results.
        
        Returns:
            Tuple of (flight_segments, hotel_stays, transport_estimates, city_order, days_per_city)
        """
        flight_segments = []
        hotel_stays = []
        transport_estimates = []
        city_order = []
        days_per_city = {}
        
        flights_found = {}
        hotels_found = {}
        
        for result in tool_results:
            tool_name = result.get("tool_name", "")
            tool_data = result.get("result", {})
            
            if tool_name == "search_flights" and tool_data.get("success"):
                cheapest = tool_data.get("cheapest_flight")
                search_params = tool_data.get("search_params", {})
                
                if cheapest:
                    from_city = search_params.get("origin", "")
                    to_city = search_params.get("destination", "")
                    
                    segment = FlightSegment(
                        from_city=from_city,
                        to_city=to_city,
                        date=search_params.get("departure_date"),
                        cost=float(cheapest.get("total_price", 0)),
                        airline=cheapest.get("validating_airline"),
                        is_estimate=False
                    )
                    
                    key = f"{from_city}-{to_city}"
                    if key not in flights_found:
                        flights_found[key] = segment
                        flight_segments.append(segment)
            
            elif tool_name == "search_hotels" and tool_data.get("success"):
                cheapest = tool_data.get("cheapest_hotel")
                search_params = tool_data.get("search_params", {})
                
                if cheapest:
                    city = search_params.get("city_code", "")
                    
                    total_price = float(cheapest.get("total_price", 0))
                    ppn = cheapest.get("price_per_night", "0")
                    try:
                        price_per_night = float(ppn)
                        nights = int(total_price / price_per_night) if price_per_night > 0 else 1
                    except:
                        nights = 1
                        price_per_night = None
                    
                    stay = HotelStay(
                        city=city,
                        nights=nights,
                        check_in=search_params.get("check_in_date"),
                        check_out=search_params.get("check_out_date"),
                        cost=total_price,
                        hotel_name=cheapest.get("hotel_name"),
                        price_per_night=price_per_night
                    )
                    
                    if city and city not in hotels_found:
                        hotels_found[city] = stay
                        hotel_stays.append(stay)
                        days_per_city[city] = nights
                        if city not in city_order:
                            city_order.append(city)
        
        return flight_segments, hotel_stays, transport_estimates, city_order, days_per_city
    
    @staticmethod
    def get_mcp_tools() -> list[dict]:
        """Define the tools schema for OpenAI function calling."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_flights",
                    "description": "Search for round-trip flights between two airports using Amadeus API",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "origin": {
                                "type": "string",
                                "description": "Origin airport IATA code (e.g., 'JFK', 'LAX', 'MAD')"
                            },
                            "destination": {
                                "type": "string",
                                "description": "Destination airport IATA code (e.g., 'CDG', 'LHR', 'ATH')"
                            },
                            "departure_date": {
                                "type": "string",
                                "description": "Departure date in YYYY-MM-DD format"
                            },
                            "return_date": {
                                "type": "string",
                                "description": "Return date in YYYY-MM-DD format"
                            },
                            "adults": {
                                "type": "integer",
                                "description": "Number of adult passengers (1-9)"
                            }
                        },
                        "required": ["origin", "destination", "departure_date", "return_date", "adults"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_hotels",
                    "description": "Search for hotels in a city",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "city_code": {
                                "type": "string",
                                "description": "City IATA code (e.g., 'PAR' for Paris, 'LON' for London)"
                            },
                            "check_in_date": {
                                "type": "string",
                                "description": "Check-in date in YYYY-MM-DD format"
                            },
                            "check_out_date": {
                                "type": "string",
                                "description": "Check-out date in YYYY-MM-DD format"
                            },
                            "adults": {
                                "type": "integer",
                                "description": "Number of adult guests",
                                "default": 1
                            }
                        },
                        "required": ["city_code", "check_in_date", "check_out_date"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_airport_code",
                    "description": "Get the IATA airport code for a city",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "city_name": {
                                "type": "string",
                                "description": "Name of the city"
                            }
                        },
                        "required": ["city_name"]
                    }
                }
            }
        ]
    
    @staticmethod
    async def call_mcp_tool(tool_name: str, args: dict) -> dict:
        """Call an MCP tool via the MCP server."""
        server_path = Path(__file__).parent.parent.parent / "mcp" / "server.py"
        
        # Import MCP adapter
        from langchain_mcp_adapters.client import MultiServerMCPClient
        from langchain_mcp_adapters.tools import load_mcp_tools
        
        mcp_client = MultiServerMCPClient({
            "coastline-travel": {
                "command": sys.executable,
                "args": [str(server_path)],
                "transport": "stdio",
            }
        })
        
        async with mcp_client.session("coastline-travel") as session:
            tools = await load_mcp_tools(session)
            
            for tool in tools:
                if tool.name == tool_name:
                    try:
                        result = await tool.ainvoke(args)
                        if isinstance(result, str):
                            return json.loads(result)
                        return result
                    except Exception as e:
                        return {"error": str(e), "success": False}
            
            return {"error": f"Tool {tool_name} not found", "success": False}
    
    @staticmethod
    async def run_single_iteration(
        budget: TripBudget,
        iteration: int,
        previous_result: BudgetResult | None = None
    ) -> tuple[BudgetResult, bool]:
        """
        Run a single iteration of the multi-city planning agent.
        
        Uses OpenAI with function calling for reliable execution.
        """
        import os
        from dotenv import load_dotenv
        load_dotenv()
        
        client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Calculate trip length
        from datetime import datetime
        start = datetime.strptime(budget.departure_date, "%Y-%m-%d")
        end = datetime.strptime(budget.return_date, "%Y-%m-%d")
        total_days = (end - start).days
        
        destinations_str = ", ".join(budget.destinations)
        
        # Add replanning context if this is not the first iteration
        replan_context = ""
        if iteration > 0 and previous_result and previous_result.breakdown:
            prev = previous_result.breakdown
            flight_cost_str = f"${prev.flight_cost:.2f}" if prev.flight_cost else "unknown"
            hotel_cost_str = f"${prev.hotel_cost:.2f}" if prev.hotel_cost else "unknown"
            replan_context = f"""

**REPLANNING ATTEMPT {iteration + 1}**
Previous attempt was over budget:
- Flight cost was {flight_cost_str} vs budget ${prev.flight_budget:.2f}
- Hotel cost was {hotel_cost_str} vs budget ${prev.hotel_budget:.2f}
- Previous city order: {' -> '.join(prev.city_order) if prev.city_order else 'N/A'}
- Previous days allocation: {prev.days_per_city}

TRY A DIFFERENT APPROACH:
- Reorder cities to find cheaper flight combinations
- Adjust number of days per city (fewer days = cheaper hotels)
- Consider if any cities are close enough for trains/buses instead of flights
"""
        
        system_prompt = """You are a budget-conscious multi-city travel planner. Your goal is to find the cheapest flights and hotels that fit within the user's budget constraints.

When searching:
1. First get airport codes for cities using get_airport_code
2. Search for flights for each leg of the journey
3. Search for hotels in each destination city

Always complete ALL searches before providing your final summary. Report exact prices from the API responses."""

        user_prompt = f"""Plan a multi-city trip with these details:

**Trip Details:**
- Origin: {budget.origin}
- Destination Cities to Visit: [{destinations_str}]
- Trip Dates: {budget.departure_date} to {budget.return_date} ({total_days} days total)
- Number of Adults: {budget.adults}

**Budget Constraints (MUST NOT EXCEED):**
- Flight Budget: ${budget.flight_budget:.2f} (for ALL flights: origin->cities->origin)
- Hotel Budget: ${budget.hotel_budget:.2f} (for ALL hotels across all cities)
- Activity Budget: ${budget.activity_budget:.2f}
- Total Budget: ${budget.flight_budget + budget.hotel_budget + budget.activity_budget:.2f}
{replan_context}

**Your Task:**
1. Decide the optimal order to visit the cities (consider geography to minimize flight costs)
2. Allocate days per city (total must equal {total_days} days)
3. Search for flights for each leg (origin->city1, city1->city2, ..., lastCity->origin)
4. Search for hotels in each city for the allocated number of nights
5. Provide a final summary with all costs

Please proceed with the searches now."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        tools = BudgetAgentService.get_mcp_tools()
        tool_results = []
        max_turns = 20
        
        for turn in range(max_turns):
            # Retry logic for rate limits
            max_retries = 3
            for retry in range(max_retries):
                try:
                    response = await client.chat.completions.create(
                        model="gpt-4o",  # Use gpt-4o (widely available) or gpt-3.5-turbo as fallback
                        messages=messages,
                        tools=tools,
                        tool_choice="auto",
                        temperature=0.2
                    )
                    break  # Success, exit retry loop
                except Exception as e:
                    if "rate_limit" in str(e).lower() or "429" in str(e):
                        wait_time = (retry + 1) * 10  # 10s, 20s, 30s
                        print(f"  Rate limited, waiting {wait_time}s...")
                        await asyncio.sleep(wait_time)
                        if retry == max_retries - 1:
                            raise  # Re-raise on final retry
                    else:
                        raise
            
            message = response.choices[0].message
            messages.append(message)
            
            # Check if the model wants to call tools
            if not message.tool_calls:
                break
            
            # Execute each tool call
            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                
                print(f"  Calling {tool_name}({tool_args})")
                
                try:
                    result = await BudgetAgentService.call_mcp_tool(tool_name, tool_args)
                except Exception as e:
                    result = {"error": str(e), "success": False}
                
                # Store result for parsing
                tool_results.append({
                    "tool_name": tool_name,
                    "args": tool_args,
                    "result": result
                })
                
                # Add tool response message
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result)
                })
        
        # Get final response content
        final_message = messages[-1].content if hasattr(messages[-1], 'content') else str(messages[-1])
        if not final_message and hasattr(messages[-1], 'get'):
            final_message = messages[-1].get('content', '')
        
        # Parse results
        flight_segments, hotel_stays, transport_estimates, city_order, days_per_city = \
            BudgetAgentService.parse_tool_results(tool_results, budget)
        
        # Build breakdown
        breakdown = BudgetAgentService.build_breakdown_from_parsed_data(
            budget, flight_segments, hotel_stays, transport_estimates,
            city_order, days_per_city
        )
        
        # Check constraints
        within_budget, errors = BudgetAgentService.check_budget_constraints(breakdown)
        
        # Calculate over-budget amount
        over_budget_amount = None
        if not within_budget:
            over_budget_amount = max(0, breakdown.total_cost - breakdown.total_budget)
            if breakdown.flight_cost and breakdown.flight_cost > breakdown.flight_budget:
                over_budget_amount = max(over_budget_amount, breakdown.flight_cost - breakdown.flight_budget)
            if breakdown.hotel_cost and breakdown.hotel_cost > breakdown.hotel_budget:
                over_budget_amount = max(over_budget_amount, breakdown.hotel_cost - breakdown.hotel_budget)
        
        budget_result = BudgetResult(
            success=within_budget,
            message="",
            iterations_used=iteration + 1,
            best_plan_over_budget=over_budget_amount,
            breakdown=breakdown,
            budget_errors=errors,
            agent_reasoning=final_message if isinstance(final_message, str) else str(final_message)
        )
        
        return budget_result, within_budget
    
    @staticmethod
    async def plan_trip_with_budget(budget: TripBudget) -> BudgetResult:
        """
        Plan a multi-city trip using the agent with iterative replanning.
        
        This method:
        1. Runs the agent to plan flights/hotels across all destination cities
        2. Checks if the plan is within budget
        3. If over budget, replans with hints to try different approaches
        4. Repeats up to max_iterations times
        5. Returns best plan found (even if over budget)
        """
        best_result: BudgetResult | None = None
        best_over_budget = float('inf')
        
        try:
            for iteration in range(budget.max_iterations):
                print(f"\n{'='*60}")
                print(f"Planning Iteration {iteration + 1}/{budget.max_iterations}")
                print(f"{'='*60}")
                
                result, within_budget = await BudgetAgentService.run_single_iteration(
                    budget, iteration, best_result
                )
                
                if within_budget:
                    result.message = (
                        f"Success! Found plan within budget after {iteration + 1} iteration(s). "
                        f"Total cost: ${result.breakdown.total_cost:.2f}"
                    )
                    return result
                
                # Track best result
                current_over = result.best_plan_over_budget or float('inf')
                if current_over < best_over_budget:
                    best_over_budget = current_over
                    best_result = result
                
                print(f"Iteration {iteration + 1}: Over budget by ${current_over:.2f}")
                
                # If we're very close to budget, might not be worth retrying
                if current_over < 50:
                    print("Close to budget - stopping iterations")
                    break
                
                # Wait between iterations to avoid rate limits
                if iteration < budget.max_iterations - 1:
                    print("Waiting 15s before next iteration (rate limit avoidance)...")
                    await asyncio.sleep(15)
            
            # All iterations exhausted - return best result
            if best_result:
                best_result.message = (
                    f"Could not meet budget after {budget.max_iterations} iterations. "
                    f"Best plan found is ${best_over_budget:.2f} over budget. "
                    f"Consider increasing your flight or hotel budget."
                )
                best_result.iterations_used = budget.max_iterations
                return best_result
            
            return BudgetResult(
                success=False,
                message="Failed to generate any valid plan",
                iterations_used=budget.max_iterations,
                budget_errors=["No valid plan could be generated"]
            )
            
        except Exception as e:
            error_message = str(e)
            import traceback
            traceback.print_exc()
            return BudgetResult(
                success=False,
                message=f"Error during trip planning: {error_message}",
                iterations_used=1,
                budget_errors=[f"Agent error: {error_message}"]
            )
