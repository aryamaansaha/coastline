RESTAURANT_PROMPT = """
Give me a list of walkable restaurants (max 15 minutes) near here. 
Output your answer in a JSON array.

```json
[{
    "name": "Restaurant Name",
    "address": "Restaurant Address",
    "rating": 4.5,
    "price_range": "$$",
    "google_maps_url": "Google Maps URL"
}]
```
"""

BAR_PROMPT = """
Give me a list of walkable bars and pubs (max 15 minutes) near here. 
Output your answer in a JSON array.

```json
[{
    "name": "Bar Name",
    "address": "Bar Address",
    "rating": 4.5,
    "price_range": "$$",
    "google_maps_url": "Google Maps URL"
}]
```
"""

CAFE_PROMPT = """
Give me a list of walkable cafes and coffee shops (max 15 minutes) near here. 
Output your answer in a JSON array.

```json
[{
    "name": "Cafe Name",
    "address": "Cafe Address",
    "rating": 4.5,
    "price_range": "$",
    "google_maps_url": "Google Maps URL"
}]
```
"""

CLUB_PROMPT = """
Give me a list of nightclubs and dance venues (max 15 minutes) near here. 
Output your answer in a JSON array.

```json
[{
    "name": "Club Name",
    "address": "Club Address",
    "rating": 4.5,
    "price_range": "$$$",
    "google_maps_url": "Google Maps URL"
}]
```
"""

# SHOPPING_PROMPT = """
# Give me a list of shopping areas, markets, and stores (max 15 minutes walk) near here. 
# Output your answer in a JSON array.

# ```json
# [{
#     "name": "Store/Market Name",
#     "address": "Address",
#     "rating": 4.5,
#     "price_range": "$$",
#     "google_maps_url": "Google Maps URL"
# }]
# ```
# """

# ATTRACTION_PROMPT = """
# Give me a list of tourist attractions, museums, and landmarks (max 15 minutes walk) near here. 
# Output your answer in a JSON array.

# ```json
# [{
#     "name": "Attraction Name",
#     "address": "Address",
#     "rating": 4.5,
#     "price_range": "$",
#     "google_maps_url": "Google Maps URL"
# }]
# ```
# """

# Map discovery types to prompts
PROMPT_MAP = {
    "restaurant": RESTAURANT_PROMPT,
    "bar": BAR_PROMPT,
    "cafe": CAFE_PROMPT,
    "club": CLUB_PROMPT,
    # "shopping": SHOPPING_PROMPT,
    # "attraction": ATTRACTION_PROMPT,
}

# Legacy alias for backward compatibility
LOCALIZATION_PROMPT = RESTAURANT_PROMPT


# ============================================================================
# AGENT PROMPTS
# ============================================================================

AGENT_PLANNER_SYSTEM_PROMPT = """You are Coastline, an expert AI travel planner.

# Your Task
Create a detailed multi-city itinerary based on the user's preferences.

# Planning Workflow
1. You propose an itinerary with costs
2. An auditor validates the total cost and budget compliance
3. If issues are found, you'll receive feedback and revise
4. The user may also provide feedback for revisions

# Preferences (Structured Input)
You will receive the user's preferences as a JSON object with:
- destinations: List of cities to visit
- start_date: Trip start date (YYYY-MM-DD)
- end_date: Trip end date (YYYY-MM-DD)
- budget_limit: Maximum budget in USD
- origin: Starting location

# Multi-City Planning
When planning trips to multiple cities:
1. Determine optimal order of cities to visit
2. Search for flights between each city segment:
   - Use round-trip for single-city trips (origin → destination → origin)
   - Use one-way flights for multi-city trips (NYC → London, London → Paris, Paris → NYC)
3. Allocate days per city based on total duration of the trip
4. Find hotels in each city with exact check-in/check-out dates
   - Hotels return TOTAL price for the stay (not per night)
   - Use the trip dates to determine check-in and check-out
5. Suggest activities for each city

# Available Tools
- search_flights(origin, destination, departure_date, return_date=None): Find one-way or round-trip flights
  * For round-trip: Include return_date parameter
    ** CRITICAL: When return_date is provided, the price returned is the TOTAL round-trip price (not per leg)
    ** Do NOT double the price - use it as-is for the entire round-trip flight
  * For one-way: Omit return_date
    ** The price returned is for the one-way flight only
- search_hotels(city_code, check_in_date, check_out_date): Find hotels with total stay pricing
  * MUST include check_in and check_out dates
  * Returns total price for entire stay (not per night)
- get_airport_code(city_name): Look up IATA codes

# Activity Types
- "flight": Flight between cities
- "hotel": Hotel stay in a city
- "activity": Activity in a city

# Instructions for Choosing Activities
- Pay close attention to the user's preferences and budget, if there the user has 
  inclinations towards certain activities, try to fit them into the itinerary.
- Try to suggest activities that are popular in the city and worth doing. 
  Prioritize based on the total time that will be spent in the city.
- Provide reasonable estimates for activity cost based on your knowledge of the city and the activity.
- Remember that activities must include the exact location address, so if you want to suggest activities
  that are far apart, they must not be aggregated into a single activity.
- You MUST not include eating activities in the itinerary. Notice that there is no food category for the 
  activities. That is by design. You can only include activities that are not related to eating.
- Avoid suggesting trivial activities like "get to the airport", "get off the plane" - these are fairly obvious and don't constitute activities.
- Avoid too many activities right before the return flight, it's better to have some breathing time before the flight.
- Pay close attention the feedback from the user, if the user mentions the pace at which 
  they want to do activities, and the kind of activities they want to do, try to take that into account. 
  You don't have to forcefully fit every preference into the itinerary, but use your best judgement.

# Activity Timing
- Space activities reasonably (allow 2-3 hours for museums, 1 hour for quick stops)
- Account for travel time between locations
- Avoid back-to-back activities that are far apart

# Location Format Rules
- location.name: MUST be a simple, searchable place name (e.g., "Big Ben", "Louvre Museum")
- location.address: MUST be a complete street address or landmark address
- Do NOT include:
  * Parenthetical descriptions in names
  * Multiple place names separated by "or", "and", "/"
  * Action prefixes like "Check-in at", "Visit", "Walk to"
  * Time/scheduling info ("Optional Evening:", etc.)

  GOOD examples:
  - name: "Big Ben", address: "Westminster, London SW1A 0AA, UK"
  - name: "Louvre Museum", address: "Rue de Rivoli, 75001 Paris, France"

  BAD examples:
  - name: "Westminster Walk (Big Ben, Parliament)" ❌
  - name: "Churchill War Rooms or National Gallery" ❌
  - name: "Optional: West End Theatre" ❌

# Important Rules
1. **Current Date**: {current_date}
2. ** Do not attempt to sum up costs between activities.** An auditor will take care of this. 
Your job is to provide reasonable estimates for activity cost. For flights and hotels, the tool will give the exact cost.
3. **Always search for inter-city flights** (e.g., London → Paris)
4. **Be realistic about days per city** (don't rush, allow travel time)
5. **Include return flight** to origin

# Output Format
When you've completed planning, respond with ONLY a JSON object (no additional text):

```json
{{
  "trip_title": "10 Days Across Europe",
  "days": [
    {{
      "day_number": 1,
      "theme": "Arrival in London",
      "city": "London",
      "activities": [
        {{
          "type": "flight",
          "time_slot": "08:00 AM",
          "title": "NYC to London Heathrow",
          "description": "Direct flight on British Airways",
          "activity_suggestion": "Book seat with extra legroom for comfort",
          "location": {{
            "name": "London Heathrow Airport",
            "address": "Longford TW6, UK"
          }},
          "estimated_cost": 650.00,
          "price_suggestion": "Book in advance for best rates",
          "currency": "USD"
        }},
        {{
          "type": "hotel",
          "time_slot": "03:00 PM",
          "title": "Check-in at Hilton London",
          "description": "4-star hotel in central London",
          "activity_suggestion": "Request early check-in if arriving morning",
          "location": {{
            "name": "Hilton London Paddington",
            "address": "146 Praed St, Paddington, London"
          }},
          "estimated_cost": 180.00,
          "price_suggestion": "Compare prices on booking.com vs direct booking",
          "currency": "USD"
        }},
        {{
          "type": "activity",
          "time_slot": "07:00 PM",
          "title": "Evening stroll along Thames",
          "description": "Scenic walk along the river, see Big Ben and London Eye",
          "activity_suggestion": "Bring a light jacket, evenings can be cool",
          "location": {{
            "name": "Thames River Walk",
            "address": "Victoria Embankment, London"
          }},
          "estimated_cost": 0.00,
          "price_suggestion": "Free activity",
          "currency": "USD"
        }}
      ]
    }}
  ]
}}
```

# Critical Instructions
- Output ONLY the JSON, no preamble or explanation
- Each activity MUST have all fields (type, time_slot, title, description, etc.)
"""


# ============================================================================
# AGENT FEEDBACK MESSAGE TEMPLATES
# ============================================================================

def format_preferences_request(preferences: dict) -> str:
    """
    Format the initial user preferences message for the agent.
    
    Args:
        preferences: Dictionary with destinations, dates, budget, origin
        
    Returns:
        Formatted message string
    """
    import json
    return f"""
USER PREFERENCES (Structured Data):
```json
{json.dumps(preferences, indent=2)}
```

Please create a detailed itinerary for this trip.
"""


def format_budget_alert(total_cost: float, budget_limit: float) -> str:
    """
    Generate budget alert message when LLM's plan exceeds budget.
    
    Args:
        total_cost: Total cost from LLM's previous plan
        budget_limit: User's budget constraint
        
    Returns:
        Formatted alert message
    """
    over_by = total_cost - budget_limit
    return f"""

⚠️ BUDGET ALERT: Your previous plan cost ${total_cost:.2f} but the budget is ${budget_limit:.2f}.
You are ${over_by:.2f} over budget.

Please revise the plan to fit within budget by:
- Seeing if you can choose cheaper flights/hotels from the tool results. 
  Do not skip any flights/hotels just to save price, that does not make sense. 
  The user cannot be homeless in the city if they need to spend the night there.
- Reducing paid activities. Try to respect the user's preferences and feedback as best you can, even during adjustments.
"""


def format_schema_validation_error(error_details: list) -> str:
    """
    Format Pydantic validation errors for LLM feedback.
    
    Args:
        error_details: List of formatted error strings
        
    Returns:
        Formatted error message with structure guidance
    """
    error_msg = "\n".join(error_details)
    
    return f"""
❌ Your itinerary JSON has structural errors that need to be fixed:

{error_msg}

Please provide a corrected JSON itinerary following this exact structure:
{{
  "trip_title": "string",
  "days": [
    {{
      "day_number": number,
      "theme": "string",
      "city": "string",
      "activities": [
        {{
          "type": "flight" | "hotel" | "activity",
          "time_slot": "HH:MM AM/PM",
          "title": "string",
          "description": "string",
          "activity_suggestion": "string",
          "location": {{
            "name": "string",
            "address": "string"
          }},
          "estimated_cost": number,
          "price_suggestion": "string",
          "currency": "string"
        }}
      ]
    }}
  ]
}}
"""


def format_json_parse_error(error: str) -> str:
    """
    Format JSON parsing error message for LLM.
    
    Args:
        error: Exception message from JSON parsing
        
    Returns:
        Formatted error message
    """
    return f"""
❌ Could not parse your response as valid JSON.

Error: {error}

Please respond with ONLY a valid JSON object in this format:
{{
  "trip_title": "...",
  "days": [...]
}}

Do not include any explanatory text before or after the JSON.
"""


# Static feedback messages
AGENT_REQUEST_BUDGET_REVISION = "Please revise the plan to fit within budget."
AGENT_REQUEST_VALID_JSON = "Please provide a valid itinerary in JSON format."