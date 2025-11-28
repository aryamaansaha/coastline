from pydantic import BaseModel

# Restaurants we obtain from the LLM given a latitude and longitude
class RestaurantLLMCreate(BaseModel):
    restaurant_name: str
    restaurant_address: str
    restaurant_rating: float
    price_range: str
    google_maps_url: str

