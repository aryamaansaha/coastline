import requests

def geocode_nominatim(query: str):
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": query, "format": "json", "limit": 1}
    headers = {"User-Agent": "travel-app"}  # required

    resp = requests.get(url, params=params, headers=headers)
    data = resp.json()
    if not data:
        return None

    return float(data[0]["lat"]), float(data[0]["lon"])

## just for testing
if __name__ == "__main__":
    lat, lng = geocode_nominatim("Times Square, New York")
    print("New York:", lat, lng)
    lat, lng = geocode_nominatim("Sagrada Familia, Barcelona")
    print("Barcelona:", lat, lng)