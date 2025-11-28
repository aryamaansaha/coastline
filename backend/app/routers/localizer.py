from fastapi import APIRouter, HTTPException
from app.services.geocode import LocalizeService
from app.schemas.trip import LocationLLMCreate, Location
from app.schemas.localizer import RestaurantLLMCreate
router = APIRouter()

# Geocode a location and return the latitude and longitude
@router.post("api/localizer/geocode", 
            response_model=Location,
            status_code=200)
def geocode_location(location: LocationLLMCreate):
    geocode_location = f"{location.name}, {location.address}"
    lat, lng = LocalizeService.geocode_nominatim(geocode_location)
    if lat is None or lng is None:
        raise HTTPException(status_code=400, detail="Failed to geocode location")
    return Location(name=location.name, address=location.address, lat=lat, lng=lng)

# Get a bunch of restaurants near a location
@router.post("api/localizer/restaurants", 
            response_model=list[RestaurantLLMCreate],
            status_code=200)
def get_restaurants(location: Location):
    restaurants, _ = LocalizeService.localize_restaurants(location.lat, location.lng, return_grounding_info=False)
    return restaurants