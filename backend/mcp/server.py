"""
Coastline MCP Server - Amadeus API Integration
===============================================
This MCP server provides tools for searching flights and hotels using the Amadeus API.
It can be used by AI agents to find the cheapest travel options.

Run with: python -m mcp.server
Or: mcp run mcp/server.py
"""

from mcp.server.fastmcp import FastMCP
from amadeus import Client, ResponseError
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize MCP server
mcp = FastMCP(name="coastline-travel")

# Initialize Amadeus client
# Uses environment variables or falls back to test credentials
amadeus = Client(
    client_id=os.getenv("AMADEUS_CLIENT_ID"),
    client_secret=os.getenv("AMADEUS_CLIENT_SECRET")
)


# ============================================================================
# FLIGHT SEARCH TOOL
# ============================================================================

@mcp.tool()
def search_flights(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str,
    adults: int
) -> dict:
    """
    Search for round-trip flights using Amadeus API and return the cheapest options.
    
    Args:
        origin: IATA airport/city code for departure (e.g., 'JFK', 'LAX', 'MAD')
        destination: IATA airport/city code for arrival (e.g., 'ATH', 'CDG', 'LHR')
        departure_date: Departure date in YYYY-MM-DD format (e.g., '2026-01-01')
        return_date: Return date in YYYY-MM-DD format (e.g., '2026-01-08')
        adults: Number of adult passengers (1-9)
    
    Returns:
        Dictionary containing:
        - success: Boolean indicating if search was successful
        - flights: List of flight offers sorted by price (cheapest first)
        - cheapest_flight: The single cheapest flight option with full details
        - total_results: Number of flights found
        - error: Error message if search failed
    """
    # Fixed parameters (not exposed to agent)
    currency = "USD"
    max_results = 10
    
    try:
        # Build request parameters
        params = {
            "originLocationCode": origin.upper(),
            "destinationLocationCode": destination.upper(),
            "departureDate": departure_date,
            "returnDate": return_date,
            "adults": adults,
            "currencyCode": currency,
            "max": max_results
        }
        
        # Make API request
        response = amadeus.shopping.flight_offers_search.get(**params)
        
        if not response.data:
            return {
                "success": True,
                "flights": [],
                "cheapest_flight": None,
                "total_results": 0,
                "message": "No flights found for the given criteria"
            }
        
        # Parse and simplify flight data
        flights = []
        for offer in response.data:
            flight_info = _parse_flight_offer(offer, response.result.get("dictionaries", {}))
            flights.append(flight_info)
        
        # Sort by price (already sorted by API, but ensure it)
        flights.sort(key=lambda x: float(x["total_price"]))
        
        return {
            "success": True,
            "flights": flights,
            "cheapest_flight": flights[0] if flights else None,
            "total_results": len(flights),
            "search_params": {
                "origin": origin.upper(),
                "destination": destination.upper(),
                "departure_date": departure_date,
                "return_date": return_date,
                "adults": adults,
                "travel_class": travel_class,
                "non_stop": non_stop
            }
        }
        
    except ResponseError as error:
        return {
            "success": False,
            "flights": [],
            "cheapest_flight": None,
            "total_results": 0,
            "error": str(error)
        }
    except Exception as e:
        return {
            "success": False,
            "flights": [],
            "cheapest_flight": None,
            "total_results": 0,
            "error": f"Unexpected error: {str(e)}"
        }


def _parse_flight_offer(offer: dict, dictionaries: dict) -> dict:
    """Parse a flight offer into a simplified structure."""
    
    # Get carrier names from dictionaries
    carriers = dictionaries.get("carriers", {})
    aircraft = dictionaries.get("aircraft", {})
    
    # Parse itineraries (outbound and optionally return)
    itineraries = []
    for itinerary in offer.get("itineraries", []):
        segments = []
        for segment in itinerary.get("segments", []):
            carrier_code = segment.get("carrierCode", "")
            segments.append({
                "departure_airport": segment.get("departure", {}).get("iataCode", ""),
                "departure_terminal": segment.get("departure", {}).get("terminal", ""),
                "departure_time": segment.get("departure", {}).get("at", ""),
                "arrival_airport": segment.get("arrival", {}).get("iataCode", ""),
                "arrival_terminal": segment.get("arrival", {}).get("terminal", ""),
                "arrival_time": segment.get("arrival", {}).get("at", ""),
                "carrier_code": carrier_code,
                "carrier_name": carriers.get(carrier_code, carrier_code),
                "flight_number": f"{carrier_code}{segment.get('number', '')}",
                "aircraft": aircraft.get(segment.get("aircraft", {}).get("code", ""), ""),
                "duration": segment.get("duration", ""),
                "stops": segment.get("numberOfStops", 0)
            })
        
        itineraries.append({
            "duration": itinerary.get("duration", ""),
            "segments": segments
        })
    
    # Parse price
    price = offer.get("price", {})
    
    # Get cabin class from first traveler's first segment
    cabin_class = "ECONOMY"
    traveler_pricings = offer.get("travelerPricings", [])
    if traveler_pricings:
        fare_details = traveler_pricings[0].get("fareDetailsBySegment", [])
        if fare_details:
            cabin_class = fare_details[0].get("cabin", "ECONOMY")
    
    return {
        "offer_id": offer.get("id", ""),
        "total_price": price.get("grandTotal", price.get("total", "0")),
        "base_price": price.get("base", "0"),
        "currency": price.get("currency", "USD"),
        "cabin_class": cabin_class,
        "itineraries": itineraries,
        "bookable_seats": offer.get("numberOfBookableSeats", 0),
        "last_ticketing_date": offer.get("lastTicketingDate", ""),
        "validating_airline": offer.get("validatingAirlineCodes", [""])[0],
        "is_one_way": offer.get("oneWay", False)
    }


# ============================================================================
# HOTEL SEARCH TOOL
# ============================================================================

@mcp.tool()
def search_hotels(
    city_code: str,
    check_in_date: str,
    check_out_date: str,
    adults: int,
    room_quantity: int = 1
) -> dict:
    """
    Search for hotels using Amadeus API and return the cheapest options.
    
    This tool first fetches hotels in the city, then gets pricing for up to 20 hotels.
    
    Args:
        city_code: IATA city code (e.g., 'ATH' for Athens, 'PAR' for Paris, 'NYC' for New York)
        check_in_date: Check-in date in YYYY-MM-DD format (e.g., '2026-01-01')
        check_out_date: Check-out date in YYYY-MM-DD format (e.g., '2026-01-08')
        adults: Number of adult guests (1-9)
        room_quantity: Number of rooms needed (default: 1)
    
    Returns:
        Dictionary containing:
        - success: Boolean indicating if search was successful
        - hotels: List of hotel offers sorted by price (cheapest first)
        - cheapest_hotel: The single cheapest hotel option with full details
        - total_results: Number of hotels with availability
        - error: Error message if search failed
    """
    # Fixed parameters (not exposed to agent)
    currency = "USD"
    best_rate_only = True
    
    try:
        # Step 1: Get list of hotels in the city
        print(f"DEBUG: Searching hotels in city: {city_code.upper()}")
        
        try:
            hotels_response = amadeus.reference_data.locations.hotels.by_city.get(
                cityCode=city_code.upper()
            )
        except ResponseError as e:
            return {
                "success": False,
                "hotels": [],
                "cheapest_hotel": None,
                "total_results": 0,
                "error": f"Failed to get hotel list for city '{city_code}': {str(e)}"
            }
        
        if not hotels_response.data:
            return {
                "success": True,
                "hotels": [],
                "cheapest_hotel": None,
                "total_results": 0,
                "message": f"No hotels found in city: {city_code}"
            }
        
        # Get first 20 hotel IDs (Amadeus test API has limits)
        # Using fewer hotels to avoid 400 errors
        hotel_ids = [hotel["hotelId"] for hotel in hotels_response.data[:20]]
        print(f"DEBUG: Found {len(hotels_response.data)} hotels, using first {len(hotel_ids)}")
        
        # Step 2: Get hotel offers with pricing
        # Try in smaller batches if needed
        all_hotels = []
        batch_size = 10  # Smaller batches are more reliable
        
        for i in range(0, len(hotel_ids), batch_size):
            batch_ids = hotel_ids[i:i + batch_size]
            
            try:
                params = {
                    "hotelIds": ",".join(batch_ids),
                    "adults": adults,
                    "checkInDate": check_in_date,
                    "checkOutDate": check_out_date,
                    "roomQuantity": room_quantity,
                    "currency": currency
                }
                
                if best_rate_only:
                    params["bestRateOnly"] = "true"
                
                print(f"DEBUG: Querying batch {i//batch_size + 1} with {len(batch_ids)} hotels")
                offers_response = amadeus.shopping.hotel_offers_search.get(**params)
                
                if offers_response.data:
                    for hotel_offer in offers_response.data:
                        if hotel_offer.get("available", False):
                            hotel_info = _parse_hotel_offer(hotel_offer)
                            if hotel_info:
                                all_hotels.append(hotel_info)
                                
            except ResponseError as batch_error:
                # Log but continue with other batches
                print(f"DEBUG: Batch {i//batch_size + 1} failed: {batch_error}")
                continue
        
        if not all_hotels:
            return {
                "success": True,
                "hotels": [],
                "cheapest_hotel": None,
                "total_results": 0,
                "hotels_searched": len(hotel_ids),
                "message": "No available rooms found for the given dates. The Amadeus test API has limited availability."
            }
        
        # Sort by price (cheapest first)
        all_hotels.sort(key=lambda x: float(x["total_price"]))
        
        return {
            "success": True,
            "hotels": all_hotels,
            "cheapest_hotel": all_hotels[0] if all_hotels else None,
            "total_results": len(all_hotels),
            "hotels_searched": len(hotel_ids),
            "search_params": {
                "city_code": city_code.upper(),
                "check_in_date": check_in_date,
                "check_out_date": check_out_date,
                "adults": adults,
                "room_quantity": room_quantity
            }
        }
        
    except ResponseError as error:
        return {
            "success": False,
            "hotels": [],
            "cheapest_hotel": None,
            "total_results": 0,
            "error": f"Amadeus API error: {str(error)}"
        }
    except Exception as e:
        return {
            "success": False,
            "hotels": [],
            "cheapest_hotel": None,
            "total_results": 0,
            "error": f"Unexpected error: {str(e)}"
        }


def _parse_hotel_offer(hotel_data: dict) -> dict | None:
    """Parse a hotel offer into a simplified structure."""
    
    hotel = hotel_data.get("hotel", {})
    offers = hotel_data.get("offers", [])
    
    if not offers:
        return None
    
    # Get the first (best) offer
    offer = offers[0]
    price = offer.get("price", {})
    room = offer.get("room", {})
    room_type = room.get("typeEstimated", {})
    policies = offer.get("policies", {})
    
    # Calculate price per night
    total = float(price.get("total", price.get("base", "0")))
    
    # Get number of nights from variations if available
    variations = price.get("variations", {})
    changes = variations.get("changes", [])
    nights = len(changes) if changes else 1
    price_per_night = total / nights if nights > 0 else total
    
    return {
        "hotel_id": hotel.get("hotelId", ""),
        "hotel_name": hotel.get("name", "Unknown Hotel"),
        "chain_code": hotel.get("chainCode", ""),
        "city_code": hotel.get("cityCode", ""),
        "latitude": hotel.get("latitude", 0),
        "longitude": hotel.get("longitude", 0),
        "offer_id": offer.get("id", ""),
        "check_in_date": offer.get("checkInDate", ""),
        "check_out_date": offer.get("checkOutDate", ""),
        "total_price": str(total),
        "base_price": price.get("base", "0"),
        "currency": price.get("currency", "USD"),
        "price_per_night": f"{price_per_night:.2f}",
        "room_type": room_type.get("category", "STANDARD_ROOM"),
        "bed_type": room_type.get("bedType", ""),
        "beds": room_type.get("beds", 1),
        "room_description": room.get("description", {}).get("text", "").replace("\n", " "),
        "board_type": offer.get("boardType", "ROOM_ONLY"),
        "is_refundable": policies.get("refundable", {}).get("cancellationRefund", "") != "NON_REFUNDABLE",
        "payment_type": policies.get("paymentType", ""),
        "adults": offer.get("guests", {}).get("adults", 1)
    }


# ============================================================================
# UTILITY TOOLS
# ============================================================================

@mcp.tool()
def get_airport_code(city_name: str) -> dict:
    """
    Look up IATA airport/city codes for a given city name.
    
    Args:
        city_name: Name of the city to search for (e.g., 'Paris', 'New York', 'Athens')
    
    Returns:
        Dictionary with matching airport/city codes and names
    """
    try:
        from amadeus import Location
        
        response = amadeus.reference_data.locations.get(
            keyword=city_name,
            subType=Location.CITY
        )
        
        if not response.data:
            # Try airport search
            response = amadeus.reference_data.locations.get(
                keyword=city_name,
                subType=Location.AIRPORT
            )
        
        if not response.data:
            return {
                "success": False,
                "locations": [],
                "message": f"No locations found for: {city_name}"
            }
        
        locations = []
        for loc in response.data[:5]:  # Return top 5 matches
            locations.append({
                "iata_code": loc.get("iataCode", ""),
                "name": loc.get("name", ""),
                "city_name": loc.get("address", {}).get("cityName", ""),
                "country_code": loc.get("address", {}).get("countryCode", ""),
                "type": loc.get("subType", "")
            })
        
        return {
            "success": True,
            "locations": locations,
            "recommended": locations[0]["iata_code"] if locations else None
        }
        
    except Exception as e:
        return {
            "success": False,
            "locations": [],
            "error": str(e)
        }


# ============================================================================
# SERVER ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    # Run the MCP server
    mcp.run()
