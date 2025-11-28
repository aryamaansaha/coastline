LOCALIZATION_PROMPT = """

Give me a list of walkable restaurants (max 15 minutes) near here. 
Output your answer in a JSON.

```json
[{
    "restaurant_name": "Restaurant Name",
    "restaurant_address": "Restaurant Address",
    "restaurant_rating": "Restaurant Rating",
    "price_range": "Price Range",
    "google_maps_url": "Google Maps URL",
},
]
```
"""