from mcp.server.fastmcp import FastMCP
from amadeus import Client, ResponseError
import os
from dotenv import load_dotenv
from typing import List, Dict, Any
import sys
import logging
from app.services.utils import retry_with_backoff
from currency import convert_to_usd

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
        
        @retry_with_backoff(max_retries=2, base_delay=1.0)
        def _fetch_flights():
            return amadeus.shopping.flight_offers_search.get(**params)
        
        response = _fetch_flights()
        
        if not response.data:
            logger.warning("No flights found in response")
            return {"flights": [], "message": "No flights found."}
        
        slim_flights = []
        dictionaries = response.result.get("dictionaries", {})
        carriers = dictionaries.get("carriers", {})

        for offer in response.data:
            # Extract only decision-critical info
            original_price = float(offer.get("price", {}).get("grandTotal", offer.get("price", {}).get("total", 0)))
            original_currency = offer.get("price", {}).get("currency", "USD")
            validating_airline = offer.get("validatingAirlineCodes", [""])[0]
            airline_name = carriers.get(validating_airline, validating_airline)
            
            # Convert price to USD for consistent budget calculations
            price_usd = convert_to_usd(original_price, original_currency)
            
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
                "price": price_usd,  # Always in USD
                "currency": "USD",
                "outbound": {
                    "departure": outbound_first_seg.get("departure", {}).get("at"),
                    "arrival": outbound_last_seg.get("arrival", {}).get("at"),
                    "duration": outbound.get("duration")
                }
            }
            
            # Include original currency info if different from USD
            if original_currency != "USD":
                flight_data["original_price"] = original_price
                flight_data["original_currency"] = original_currency
            
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
        # 1. Get hotels in city (with retry for rate limiting)
        @retry_with_backoff(max_retries=2, base_delay=1.0)
        def _fetch_hotels_by_city():
            return amadeus.reference_data.locations.hotels.by_city.get(
                cityCode=city_code.upper()
            )
        
        hotels_resp = _fetch_hotels_by_city()
        
        if not hotels_resp.data:
            logger.warning("No hotels found in response")
            return {"hotels": [], "message": "No hotels found."}
            
        # Get 15 hotel IDs to increase chances of valid results
        TARGET_RESULTS = 5
        FALLBACK_RESULTS = 5  # If batch fails, only try 3 individually
        hotel_ids = [h["hotelId"] for h in hotels_resp.data[:15]]
        logger.info(f"Found {len(hotel_ids)} hotels, fetching offers...")
        
        slim_hotels = []
        
        # 2. Try batch request first (most efficient)
        try:
            offers_resp = amadeus.shopping.hotel_offers_search.get(
                hotelIds=",".join(hotel_ids),
                adults=1,
                checkInDate=check_in_date,
                checkOutDate=check_out_date,
                currency="USD"
            )
            
            # Process batch results
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
                    
                    # Calculate total price in original currency
                    original_total = float(price.get("total", price.get("base", "0")))
                    original_currency = price.get("currency", "USD")
                    
                    # Convert to USD for consistent budget calculations
                    total_usd = convert_to_usd(original_total, original_currency)
                    price_per_night_usd = total_usd / nights if nights > 0 else total_usd
                    
                    hotel_data = {
                        "name": hotel_name,
                        "hotel_id": hotel.get("hotelId"),
                        "total_price": total_usd,  # Always in USD
                        "price_per_night": round(price_per_night_usd, 2),
                        "currency": "USD",
                        "rating": hotel.get("rating", "N/A"),
                        "nights": nights
                    }
                    
                    # Include original currency info if different from USD
                    if original_currency != "USD":
                        hotel_data["original_total"] = round(original_total, 2)
                        hotel_data["original_currency"] = original_currency
                    
                    slim_hotels.append(hotel_data)
            
            logger.info(f"Batch request successful, got {len(slim_hotels)} valid hotels")
        
        except ResponseError as batch_error:
            # Batch failed (likely one bad hotel ID) - try individually with limit
            logger.warning(f"Batch hotel request failed: {batch_error}")
            logger.info(f"Trying first {FALLBACK_RESULTS} hotels individually (API call limit)...")
            
            for hotel_id in hotel_ids[:FALLBACK_RESULTS]:
                if len(slim_hotels) >= FALLBACK_RESULTS:
                    break  # Already have enough
                
                try:
                    offers_resp = amadeus.shopping.hotel_offers_search.get(
                        hotelIds=hotel_id,  # One at a time
                        adults=1,
                        checkInDate=check_in_date,
                        checkOutDate=check_out_date,
                        currency="USD"
                    )
                    
                    if not offers_resp.data:
                        continue
                    
                    # Process individual result
                    for offer in offers_resp.data:
                        if not offer.get("available", False):
                            continue
                        
                        hotel = offer.get("hotel", {})
                        offers_list = offer.get("offers", [])
                        hotel_name = (hotel.get("name") or "").strip()
                        
                        if hotel_name.lower() == "test property":
                            continue
                        
                        if not offers_list:
                            continue
                        
                        best_offer = offers_list[0]
                        price = best_offer.get("price", {})
                        
                        # Calculate total price in original currency
                        original_total = float(price.get("total", price.get("base", "0")))
                        original_currency = price.get("currency", "USD")
                        
                        # Convert to USD for consistent budget calculations
                        total_usd = convert_to_usd(original_total, original_currency)
                        price_per_night_usd = total_usd / nights if nights > 0 else total_usd
                        
                        hotel_data = {
                            "name": hotel_name,
                            "hotel_id": hotel.get("hotelId"),
                            "total_price": total_usd,  # Always in USD
                            "price_per_night": round(price_per_night_usd, 2),
                            "currency": "USD",
                            "rating": hotel.get("rating", "N/A"),
                            "nights": nights
                        }
                        
                        # Include original currency info if different from USD
                        if original_currency != "USD":
                            hotel_data["original_total"] = round(original_total, 2)
                            hotel_data["original_currency"] = original_currency
                        
                        slim_hotels.append(hotel_data)
                        
                except ResponseError as individual_error:
                    logger.warning(f"Skipping invalid hotel {hotel_id}: {individual_error}")
                    continue
            
            logger.info(f"Fallback completed, got {len(slim_hotels)} valid hotels")
        
        # Sort by price and return top 5 (or whatever we got)
        slim_hotels.sort(key=lambda x: x["total_price"])
        result_count = min(len(slim_hotels), TARGET_RESULTS)
        logger.info(f"Returning {result_count} hotels (requested {TARGET_RESULTS})")
        return {"hotels": slim_hotels[:TARGET_RESULTS]}

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
    
    @retry_with_backoff(max_retries=2, base_delay=1.0)
    def _fetch_airport_code():
        from amadeus import Location
        response = amadeus.reference_data.locations.get(
            keyword=city_name, subType=Location.CITY
        )
        if not response.data:
            return {"error": "City not found"}
        
        loc = response.data[0]
        return {
            "name": loc.get("name"),
            "iata_code": loc.get("iataCode")
        }
    
    try:
        return _fetch_airport_code()
    except ResponseError as e:
        logger.error(f"Amadeus API Error in get_airport_code: {e}")
        return {"error": f"API Error: {str(e)}"}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    mcp.run()

