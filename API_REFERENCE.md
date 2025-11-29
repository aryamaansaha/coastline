# Coastline API Reference

**Base URL:** `http://localhost:8008`  
**Docs:** http://localhost:8008/docs (Swagger UI)

---

## Data Models

### Preferences (Input)
```json
{
  "destinations": ["Paris"],
  "start_date": "2024-06-01T00:00:00",
  "end_date": "2024-06-03T00:00:00",
  "budget_limit": 500.0
}
```

### Itinerary (Output)
```json
{
  "trip_id": "uuid-string",
  "trip_title": "2 Days in Paris",
  "budget_limit": 500.0,
  "days": [
    {
      "id": "day-uuid",
      "day_number": 1,
      "theme": "Art & History",
      "activities": [
        {
          "id": "activity-uuid",
          "type": "activity",  // "flight" | "hotel" | "activity"
          "time_slot": "2024-06-01T09:00:00",
          "title": "Eiffel Tower Visit",
          "description": "...",
          "activity_suggestion": "Arrive early to avoid crowds...",
          "location": {
            "name": "Eiffel Tower",
            "address": "Champ de Mars, Paris",
            "lat": 48.8584,
            "lng": 2.2945
          },
          "estimated_cost": 28.0,
          "price_suggestion": "Book online for discounts",
          "currency": "USD"
        }
      ]
    }
  ]
}
```

### DiscoveredPlace
```json
{
  "id": "place-uuid",
  "place_type": "restaurant",  // "bar" | "cafe" | "club" 
  "name": "Le Petit Cler",
  "address": "29 Rue Cler, Paris",
  "rating": 4.5,
  "price_range": "$$",  // "$" | "$$" | "$$$" | "N/A"
  "google_maps_url": "https://maps.google.com/...",
  "lat": 48.8572,
  "lng": 2.3059,
  "starred": false
}
```

---

## Trip Endpoints

### Generate Trip
```http
POST /api/trip/generate
Content-Type: application/json

Body: Preferences object
Returns: Itinerary object with trip_id
```

**Example:**
```bash
curl -X POST http://localhost:8008/api/trip/generate \
  -H "Content-Type: application/json" \
  -d '{"destinations":["Paris"],"start_date":"2024-06-01T00:00:00","end_date":"2024-06-03T00:00:00","budget_limit":500}'
```

### Get Trip
```http
GET /api/trip/{trip_id}

Returns: Itinerary object
```

### Update Trip
```http
PUT /api/trip/{trip_id}
Content-Type: application/json

Body: Complete Itinerary object
```

### Delete Trip
```http
DELETE /api/trip/{trip_id}

Returns: {"success": true}
Note: Cascades to all discoveries
```

---

## Discovery Endpoints

### Discover Places
```http
POST /api/trip/{trip_id}/activities/{activity_id}/discover/{place_type}
Query: ?regenerate=false

Place Types: restaurant | bar | cafe | club | shopping | attraction

Returns: Array of DiscoveredPlace
```

**Behavior:**
- First call: Fetches from Gemini, caches in MongoDB
- Subsequent calls: Returns cached data (no API cost)
- `?regenerate=true`: Keeps starred places, fetches new ones from Gemini

**Examples:**
```bash
# Discover restaurants
curl -X POST "http://localhost:8008/api/trip/{trip_id}/activities/{activity_id}/discover/restaurant"

# Discover bars
curl -X POST "http://localhost:8008/api/trip/{trip_id}/activities/{activity_id}/discover/bar"

# Regenerate restaurants (keeps starred)
curl -X POST "http://localhost:8008/api/trip/{trip_id}/activities/{activity_id}/discover/restaurant?regenerate=true"
```

### Star/Unstar Place
```http
PUT /api/trip/{trip_id}/activities/{activity_id}/discover/{place_type}/{place_id}/star
Content-Type: application/json

Body: {"starred": true}
Returns: {"success": true, "starred": true}
```

### Get All Discoveries
```http
GET /api/trip/{trip_id}/discoveries
Query: ?place_type=restaurant (optional filter)

Returns: Array of discoveries with activity context
```

**Response:**
```json
[
  {
    "activity_id": "uuid",
    "activity_name": "Eiffel Tower Visit",
    "discovery_type": "restaurant",
    "discovered_at": "2024-11-29T14:30:00",
    "places": [...]
  }
]
```

### Delete Discovery
```http
DELETE /api/trip/{trip_id}/activities/{activity_id}/discover/{place_type}

Returns: {"success": true}
Note: Clears all places for this activity/type
```

---

## Localizer Endpoints (Utilities)

### Geocode Address
```http
POST /api/localizer/geocode
Content-Type: application/json

Body: {"name": "Eiffel Tower", "address": "Paris"}
Returns: {"name": "...", "address": "...", "lat": 48.8584, "lng": 2.2945}
```

### Get Restaurants (Stateless)
```http
POST /api/localizer/restaurants
Content-Type: application/json

Body: Location object with lat/lng
Returns: Array of restaurants (not persisted)
```

---

## User Flow

```
1. Generate trip
   POST /api/trip/generate → Returns trip_id

2. View itinerary
   GET /api/trip/{trip_id} → Shows days & activities

3. Discover restaurants for activity
   POST /api/trip/{trip_id}/activities/{activity_id}/discover/restaurant
   → Returns 15-20 restaurants (cached)

4. Star favorites
   PUT /api/trip/{trip_id}/activities/{activity_id}/discover/restaurant/{place_id}/star
   Body: {"starred": true}

5. Regenerate (keeps starred)
   POST /api/trip/{trip_id}/activities/{activity_id}/discover/restaurant?regenerate=true
   → Starred places + new suggestions

6. View all discoveries
   GET /api/trip/{trip_id}/discoveries
   → All restaurants, bars, cafes discovered
```

---

## Important Notes

### LLM Schema Patterns
- Models ending with `LLMCreate` are generated by the agent (e.g., `ActivityLLMCreate`)
- Final models add IDs and computed fields (e.g., `Activity` adds `id`, geocoded `location`)
- Don't generate IDs in LLM output - backend assigns them

### Discovery Caching
- Each (trip_id, activity_id, place_type) combination is cached independently
- Same activity can have restaurants, bars, AND cafes
- Regeneration merges starred + new places (no deduplication currently)

### Coordinates
- Activity locations: From agent output (geocoded if needed)
- Discovered places: Geocoded via Nominatim (OpenStreetMap)
- Geocoding can fail → defaults to (0.0, 0.0)
- Rate limit: ~1 req/sec for Nominatim

### MongoDB Collections
- `itineraries` - Trip data (indexed on `trip_id`)
- `discoveries` - Place discoveries (compound index on `trip_id`, `activity_id`, `discovery_type`)

---


## Setup

```bash
# Install dependencies
pip install -r backend/requirements.txt

# Set environment variables
MONGODB_URI=mongodb://localhost:27017/
GOOGLE_API_KEY=your_gemini_api_key

# Start MongoDB
docker run -d --name mongodb -p 27017:27017 mongo

# Run server
cd backend
uvicorn app.main:app --reload --port 8008
```

