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

SHOPPING_PROMPT = """
Give me a list of shopping areas, markets, and stores (max 15 minutes walk) near here. 
Output your answer in a JSON array.

```json
[{
    "name": "Store/Market Name",
    "address": "Address",
    "rating": 4.5,
    "price_range": "$$",
    "google_maps_url": "Google Maps URL"
}]
```
"""

ATTRACTION_PROMPT = """
Give me a list of tourist attractions, museums, and landmarks (max 15 minutes walk) near here. 
Output your answer in a JSON array.

```json
[{
    "name": "Attraction Name",
    "address": "Address",
    "rating": 4.5,
    "price_range": "$",
    "google_maps_url": "Google Maps URL"
}]
```
"""

# Map discovery types to prompts
PROMPT_MAP = {
    "restaurant": RESTAURANT_PROMPT,
    "bar": BAR_PROMPT,
    "cafe": CAFE_PROMPT,
    "club": CLUB_PROMPT,
    "shopping": SHOPPING_PROMPT,
    "attraction": ATTRACTION_PROMPT,
}

# Legacy alias for backward compatibility
LOCALIZATION_PROMPT = RESTAURANT_PROMPT