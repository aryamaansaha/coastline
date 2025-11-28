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
from app.prompts import LOCALIZATION_PROMPT
from app.services.utils import ResponseParser
load_dotenv()

def geocode_nominatim(query: str):
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": query, "format": "json", "limit": 1}
    headers = {"User-Agent": "travel-app"}  # required

    resp = requests.get(url, params=params, headers=headers)
    data = resp.json()
    if not data:
        return None

    return float(data[0]["lat"]), float(data[0]["lon"])

def localize_restaurants(lat: float, lng: float, return_grounding_info: bool = False):
    prompt = LOCALIZATION_PROMPT
    client = genai.Client()
    print(f"DEBUG: Calling API with lat={lat}, lng={lng}")
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
    print(f"DEBUG: API response: {response.text[:200]}")



    grounding = response.candidates[0].grounding_metadata
    # print("\nGrounding metadata:", grounding)

    # if grounding and grounding.grounding_chunks:
    #     print("\nSources:")
    #     for chunk in grounding.grounding_chunks:
    #         if chunk.maps:
    #             print(f"- {chunk.maps.title}: {chunk.maps.uri}")
    # else:
    #     print("\n(No Google Maps grounding – tool probably not used)")

    if return_grounding_info:
        return ResponseParser.extract_json(response.text), grounding
    else:
        return ResponseParser.extract_json(response.text), None


## just for testing
if __name__ == "__main__":
    import json

    def pretty_print(title, obj):
        print(f"\n{title}:")
        print(json.dumps(obj, indent=2, ensure_ascii=False))

    # lat, lng = geocode_nominatim("Times Square, New York")
    # pretty_print("New York Coordinates", {"lat": lat, "lng": lng})
    # restaurants_ny, grounding_ny = localize_restaurants(lat, lng, return_grounding_info=True)
    # pretty_print("Restaurants near Times Square, New York", restaurants_ny)

    # lat, lng = geocode_nominatim("Sagrada Familia, Barcelona")
    # pretty_print("Barcelona Coordinates", {"lat": lat, "lng": lng})
    # restaurants_bcn, grounding_bcn = localize_restaurants(lat, lng, return_grounding_info=True)
    # pretty_print("Restaurants near Sagrada Familia, Barcelona", restaurants_bcn)
    
    lat, lng = geocode_nominatim("Taj Mahal, Agra")
    pretty_print("Taj Mahal Coordinates", {"lat": lat, "lng": lng})
    restaurants_taj, grounding_taj = localize_restaurants(lat, lng, return_grounding_info=True)
    pretty_print("Restaurants near Taj Mahal, Agra", restaurants_taj)
    