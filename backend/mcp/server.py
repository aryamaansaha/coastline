from mcp.server.fastmcp import FastMCP
from amadeus import Client, ResponseError
import os
from dotenv import load_dotenv
from typing import List, Dict, Any
import sys
import logging

# Setup logging to stderr
logging.basicConfig(
    level=logging.INFO,
    format='[MCP Server] %(levelname)s: %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

load_dotenv()

# Initialize MCP server
mcp = FastMCP(name="coastline-travel")

# Initialize Amadeus client
amadeus_client_id = os.getenv("AMADEUS_CLIENT_ID")
amadeus_client_secret = os.getenv("AMADEUS_CLIENT_SECRET")

if not amadeus_client_id or not amadeus_client_secret:
    logger.error("AMADEUS credentials not found in environment variables!")
else:
    logger.info("AMADEUS credentials loaded successfully")

amadeus = Client(
    client_id=amadeus_client_id,
    client_secret=amadeus_client_secret
)

# ============================================================================
# HELPER: BUDGET CALCULATOR
# ============================================================================

@mcp.tool()
def calculate_itinerary_cost(line_items: List[Dict[str, Any]]) -> dict:
    """
    Calculate the total cost of a trip based on a list of items.
    ALWAYS use this tool to sum up costs. Do not do math yourself.
    
    Args:
        line_items: List of dicts, e.g., [{"category": "flight", "amount": 500.0, "description": "..."}, ...]
    """
    total = 0.0
    breakdown = {}
    
    for item in line_items:
        try:
            amount = float(item.get("amount", 0))
            category = item.get("category", "misc")
            total += amount
            
            if category not in breakdown:
                breakdown[category] = 0.0
            breakdown[category] += amount
        except (ValueError, TypeError):
            continue
            
    return {
        "total_cost": round(total, 2),
        "currency": "USD",
        "category_breakdown": {k: round(v, 2) for k, v in breakdown.items()},
        "item_count": len(line_items)
    }

# ============================================================================
# FLIGHT SEARCH TOOL (SLIM + ROUND-TRIP)
# ============================================================================

@mcp.tool()
def search_flights(origin: str, destination: str, departure_date: str, return_date: str = None) -> dict:
    """
    Search for flights. Supports both one-way and round-trip.
    Returns simplified data for decision making.
    
    Args:
        origin: 3-letter IATA airport code (e.g., "JFK", "NYC")
        destination: 3-letter IATA airport code (e.g., "LON", "LHR")
        departure_date: Departure date in YYYY-MM-DD format (must be in the future)
        return_date: (Optional) Return date for round-trip in YYYY-MM-DD format
    
    Returns:
        Dict with 'flights' list or 'error' message
    """
    trip_type = "round-trip" if return_date else "one-way"
    logger.info(f"Searching {trip_type} flights: {origin} -> {destination} departing {departure_date}")
    
    try:
        params = {
            "originLocationCode": origin.upper(),
            "destinationLocationCode": destination.upper(),
            "departureDate": departure_date,
            "adults": 1,
            "currencyCode": "USD",
            "max": 10
        }
        
        # Add return date if round-trip
        if return_date:
            params["returnDate"] = return_date
        
        response = amadeus.shopping.flight_offers_search.get(**params)
        
        if not response.data:
            logger.warning("No flights found in response")
            return {"flights": [], "message": "No flights found."}
        
        slim_flights = []
        dictionaries = response.result.get("dictionaries", {})
        carriers = dictionaries.get("carriers", {})

        for offer in response.data:
            # Extract only decision-critical info
            price = offer.get("price", {}).get("grandTotal", offer.get("price", {}).get("total"))
            currency = offer.get("price", {}).get("currency", "USD")
            validating_airline = offer.get("validatingAirlineCodes", [""])[0]
            airline_name = carriers.get(validating_airline, validating_airline)
            
            # Get itinerary details (outbound and return if round-trip)
            itineraries = offer.get("itineraries", [])
            if not itineraries: continue
            
            # Outbound (first itinerary)
            outbound = itineraries[0]
            outbound_first_seg = outbound.get("segments", [])[0] if outbound.get("segments") else {}
            outbound_last_seg = outbound.get("segments", [])[-1] if outbound.get("segments") else {}
            
            flight_data = {
                "id": offer.get("id"),
                "airline": airline_name,
                "price": float(price),
                "currency": currency,
                "outbound": {
                    "departure": outbound_first_seg.get("departure", {}).get("at"),
                    "arrival": outbound_last_seg.get("arrival", {}).get("at"),
                    "duration": outbound.get("duration")
                }
            }
            
            # Add return leg if round-trip
            if len(itineraries) > 1:
                return_leg = itineraries[1]
                return_first_seg = return_leg.get("segments", [])[0] if return_leg.get("segments") else {}
                return_last_seg = return_leg.get("segments", [])[-1] if return_leg.get("segments") else {}
                
                flight_data["return"] = {
                    "departure": return_first_seg.get("departure", {}).get("at"),
                    "arrival": return_last_seg.get("arrival", {}).get("at"),
                    "duration": return_leg.get("duration")
                }
            
            slim_flights.append(flight_data)
            
        # Sort by price
        slim_flights.sort(key=lambda x: x["price"])
        logger.info(f"Found {len(slim_flights)} flights, returning top 5")
        return {"flights": slim_flights[:5]}

    except ResponseError as e:
        logger.error(f"Amadeus API Error: {e}")
        return {"error": f"API Error: {str(e)}"}
    except Exception as e:
        logger.error(f"Unexpected error in search_flights: {type(e).__name__}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {"error": str(e)}

# ============================================================================
# HOTEL SEARCH TOOL (SLIM + DATES + TOTAL STAY PRICE)
# ============================================================================

@mcp.tool()
def search_hotels(city_code: str, check_in_date: str, check_out_date: str) -> dict:
    """
    Search for hotels with check-in/check-out dates.
    Returns total stay price (not per-night).
    
    Args:
        city_code: 3-letter IATA city code (e.g., "LON", "PAR", "NYC")
        check_in_date: Check-in date in YYYY-MM-DD format
        check_out_date: Check-out date in YYYY-MM-DD format
    
    Returns:
        Dict with 'hotels' list or 'error' message
    """
    logger.info(f"Searching hotels in: {city_code} from {check_in_date} to {check_out_date}")
    
    # Calculate nights from actual dates
    from datetime import datetime
    check_in_dt = datetime.strptime(check_in_date, "%Y-%m-%d")
    check_out_dt = datetime.strptime(check_out_date, "%Y-%m-%d")
    nights = (check_out_dt - check_in_dt).days
    
    try:
        # 1. Get hotels in city
        hotels_resp = amadeus.reference_data.locations.hotels.by_city.get(
            cityCode=city_code.upper()
        )
        
        if not hotels_resp.data:
            logger.warning("No hotels found in response")
            return {"hotels": [], "message": "No hotels found."}
            
        # Limit to 5 hotels for pricing to save time/tokens
        hotel_ids = [h["hotelId"] for h in hotels_resp.data[:5]]
        logger.info(f"Found {len(hotel_ids)} hotels, fetching offers...")
        
        # 2. Get offers with dates
        offers_resp = amadeus.shopping.hotel_offers_search.get(
            hotelIds=",".join(hotel_ids),
            adults=1,
            checkInDate=check_in_date,
            checkOutDate=check_out_date,
            currency="USD"
        )
        
        slim_hotels = []
        if offers_resp.data:
            for offer in offers_resp.data:
                if not offer.get("available", False):
                    continue
                    
                hotel = offer.get("hotel", {})
                offers_list = offer.get("offers", [])
                
                # Filter out known test/sandbox properties from Amadeus
                hotel_name = (hotel.get("name") or "").strip()
                if hotel_name.lower() == "test property":
                    logger.info("Skipping test/sandbox hotel property")
                    continue
                
                if not offers_list:
                    continue
                
                # Get first (best) offer
                best_offer = offers_list[0]
                price = best_offer.get("price", {})
                
                # Calculate total price
                total = float(price.get("total", price.get("base", "0")))
                
                # Calculate per-night price (simple division is most accurate)
                price_per_night = total / nights if nights > 0 else total
                
                slim_hotels.append({
                    "name": hotel_name,
                    "hotel_id": hotel.get("hotelId"),
                    "total_price": round(total, 2),  # Total for entire stay
                    "price_per_night": round(price_per_night, 2),  # Accurate per-night
                    "currency": price.get("currency", "USD"),
                    "rating": hotel.get("rating", "N/A"),
                    "nights": nights  # Include for transparency
                })
        
        slim_hotels.sort(key=lambda x: x["total_price"])
        logger.info(f"Returning {len(slim_hotels)} hotels")
        return {"hotels": slim_hotels}

    except ResponseError as e:
        logger.error(f"Amadeus API Error in hotels: {e}")
        return {"error": f"API Error: {str(e)}"}
    except Exception as e:
        logger.error(f"Unexpected error in search_hotels: {type(e).__name__}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {"error": str(e)}

# ============================================================================
# UTILITY
# ============================================================================

@mcp.tool()
def get_airport_code(city_name: str) -> dict:
    """Look up IATA codes for a city."""
    try:
        from amadeus import Location
        response = amadeus.reference_data.locations.get(
            keyword=city_name, subType=Location.CITY
        )
        if not response.data: return {"error": "City not found"}
        
        loc = response.data[0]
        return {
            "name": loc.get("name"),
            "iata_code": loc.get("iataCode")
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    mcp.run()

