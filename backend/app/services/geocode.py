import sys
from pathlib import Path

# Add the backend directory to sys.path to allow running this script directly
backend_dir = Path(__file__).resolve().parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import requests
from google import genai
from google.genai import types
from dotenv import load_dotenv
from app.services.utils import ResponseParser
from pydantic import ValidationError

load_dotenv()

class LocalizeService:
    @staticmethod
    def geocode_nominatim(query: str):
        url = "https://nominatim.openstreetmap.org/search"
        params = {"q": query, "format": "json", "limit": 1}
        headers = {"User-Agent": "travel-app"}  # required

        resp = requests.get(url, params=params, headers=headers)
        data = resp.json()
        if not data:
            return None

        return float(data[0]["lat"]), float(data[0]["lon"])

    @staticmethod
    def localize_restaurants(lat: float, lng: float, return_grounding_info: bool = False):
        """Legacy method - calls discover_places with restaurant prompt"""
        return LocalizeService.discover_places(
            lat, lng, "restaurant", return_grounding_info
        )
    
    @staticmethod
    def discover_places(lat: float, lng: float, place_type: str = "restaurant", return_grounding_info: bool = False):
        """
        Generic place discovery using Gemini + Google Maps grounding.
        Validates LLM output against PlaceLLMCreate schema with 1 retry on failure.
        
        Args:
            lat: Latitude
            lng: Longitude
            place_type: Type of place (restaurant, bar, cafe, club, shopping, attraction)
            return_grounding_info: Whether to return grounding metadata
        
        Returns:
            Tuple of (validated_places_list, grounding_metadata)
        """
        from app.prompts import PROMPT_MAP
        from app.schemas.discovery import PlaceLLMCreate
        
        MAX_RETRIES = 2  # 1 initial + 1 retry
        prompt = PROMPT_MAP.get(place_type, PROMPT_MAP["restaurant"])
        client = genai.Client()
        
        last_error = None
        last_grounding = None
        
        for attempt in range(MAX_RETRIES):
            print(f"[Discovery] Discovering {place_type} near ({lat:.4f}, {lng:.4f}) - attempt {attempt + 1}/{MAX_RETRIES}")
            
            try:
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        tools=[types.Tool(google_maps=types.GoogleMaps(enable_widget=True))],
                        tool_config=types.ToolConfig(
                            retrieval_config=types.RetrievalConfig(
                                lat_lng=types.LatLng(latitude=lat, longitude=lng)
                            )
                        ),
                    ),
                )
                
                print(f"[Discovery] API response preview: {response.text[:150]}...")
                
                # Get grounding metadata
                last_grounding = None
                if response.candidates and response.candidates[0].grounding_metadata:
                    last_grounding = response.candidates[0].grounding_metadata
                
                # Parse JSON from response
                raw_places = ResponseParser.extract_json(response.text)
                
                if not raw_places:
                    last_error = "Failed to extract JSON from LLM response"
                    print(f"[Discovery] ⚠️ {last_error}")
                    continue
                
                # Handle single place response
                if not isinstance(raw_places, list):
                    raw_places = [raw_places]
                
                # Validate each place against schema
                validated_places = []
                validation_errors = []
                
                for i, place in enumerate(raw_places):
                    try:
                        validated = PlaceLLMCreate(**place)
                        validated_places.append(validated.model_dump())
                    except ValidationError as e:
                        validation_errors.append(f"Place {i} ({place.get('name', 'unknown')}): {e.errors()[0]['msg']}")
                
                # Log validation results
                if validated_places:
                    print(f"[Discovery] ✅ Validated {len(validated_places)}/{len(raw_places)} places")
                    if validation_errors:
                        print(f"[Discovery] ⚠️ Skipped invalid places: {len(validation_errors)}")
                        for err in validation_errors[:3]:  # Show first 3 errors
                            print(f"   - {err}")
                    
                    if return_grounding_info:
                        return validated_places, last_grounding
                    else:
                        return validated_places, None
                
                # No valid places - will retry
                last_error = f"All {len(raw_places)} places failed validation"
                print(f"[Discovery] ⚠️ {last_error}")
                
            except Exception as e:
                last_error = f"API error: {str(e)}"
                print(f"[Discovery] ❌ {last_error}")
        
        # All retries exhausted
        print(f"[Discovery] ❌ Discovery failed after {MAX_RETRIES} attempts: {last_error}")
        
        if return_grounding_info:
            return [], last_grounding
        else:
            return [], None


## just for testing
if __name__ == "__main__":
    import json

    def pretty_print(title, obj):
        print(f"\n{title}:")
        print(json.dumps(obj, indent=2, ensure_ascii=False))

    # lat, lng = LocalizeService.geocode_nominatim("Times Square, New York")
    # pretty_print("New York Coordinates", {"lat": lat, "lng": lng})
    # restaurants_ny, grounding_ny = LocalizeService.localize_restaurants(lat, lng, return_grounding_info=True)
    # pretty_print("Restaurants near Times Square, New York", restaurants_ny)

    # lat, lng = LocalizeService.geocode_nominatim("Sagrada Familia, Barcelona")
    # pretty_print("Barcelona Coordinates", {"lat": lat, "lng": lng})
    # restaurants_bcn, grounding_bcn = LocalizeService.localize_restaurants(lat, lng, return_grounding_info=True)
    # pretty_print("Restaurants near Sagrada Familia, Barcelona", restaurants_bcn)
    
    # lat, lng = LocalizeService.geocode_nominatim("Taj Mahal, Agra")
    # pretty_print("Taj Mahal Coordinates", {"lat": lat, "lng": lng})
    # restaurants_taj, grounding_taj = LocalizeService.localize_restaurants(lat, lng, return_grounding_info=True)
    # pretty_print("Restaurants near Taj Mahal, Agra", restaurants_taj)
    