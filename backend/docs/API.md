# API Reference

## Base URL

```
http://localhost:8000
```

## Endpoints

### Trip Generation (HITL)

#### Start Trip Generation

```http
POST /api/trip/generate/stream
Content-Type: application/json
```

**Request Body:**
```json
{
  "destinations": ["London", "Paris"],
  "start_date": "2024-03-15T00:00:00Z",
  "end_date": "2024-03-22T00:00:00Z",
  "budget_limit": 3000.0,
  "origin": "New York"
}
```

**Response:** Server-Sent Events stream (see [SSE.md](./SSE.md))

---

#### Submit Decision

```http
POST /api/trip/session/{session_id}/decide
Content-Type: application/json
```

**Request Body:**
```json
{
  "action": "approve" | "revise",
  "feedback": "Add more nature activities",  // Optional
  "new_budget": 3500.0                        // Optional
}
```

**Response:** SSE stream with updated itinerary or completion

---

#### Get Session Status

```http
GET /api/trip/session/{session_id}/status
```

**Response:**
```json
{
  "session_id": "abc123",
  "status": "awaiting_approval" | "processing" | "complete" | "failed",
  "revision_count": 1,
  "created_at": "2024-03-15T10:00:00Z"
}
```

---

#### Delete Session

```http
DELETE /api/trip/session/{session_id}
```

**Response:** `204 No Content`

---

### Trip CRUD

#### List All Trips

```http
GET /api/trips
```

**Response:**
```json
[
  {
    "trip_id": "trip_123",
    "trip_title": "8 Days in London and Paris",
    "budget_limit": 3000.0,
    "destinations": ["London", "Paris"],
    "num_days": 8,
    "created_at": "2024-03-15T10:00:00Z",
    "updated_at": "2024-03-15T12:00:00Z"
  }
]
```

---

#### Get Trip Details

```http
GET /api/trip/{trip_id}
```

**Response:**
```json
{
  "trip_id": "trip_123",
  "trip_title": "8 Days in London and Paris",
  "budget_limit": 3000.0,
  "days": [
    {
      "id": "day_1",
      "day_number": 1,
      "theme": "Departure from Seattle",
      "city": "Seattle",
      "activities": [
        {
          "id": "act_1",
          "type": "flight",
          "time_slot": "02:35 PM",
          "title": "Flight to London",
          "description": "...",
          "activity_suggestion": "...",
          "location": {
            "name": "Seattle-Tacoma International Airport",
            "address": "17801 International Blvd, Seattle, WA",
            "lat": 47.4502,
            "lng": -122.3088
          },
          "estimated_cost": 385.0,
          "price_suggestion": "...",
          "currency": "USD"
        }
      ]
    }
  ]
}
```

---

#### Update Trip

```http
PUT /api/trip/{trip_id}
Content-Type: application/json
```

**Request Body:** Full `Itinerary` object

**Response:** Updated `Itinerary`

---

#### Delete Trip

```http
DELETE /api/trip/{trip_id}
```

**Response:** `204 No Content`

---

### Discovery

#### Discover Places Near Activity

```http
POST /api/trip/{trip_id}/activities/{activity_id}/discover/{place_type}?regenerate=false
```

**Path Parameters:**
- `place_type`: `restaurant` | `bar` | `cafe` | `attraction` | `nightlife`

**Query Parameters:**
- `regenerate`: `true` to fetch new places (keeps starred)

**Response:**
```json
[
  {
    "id": "place_1",
    "name": "The Ivy",
    "address": "1-5 West St, London",
    "lat": 51.5115,
    "lng": -0.1270,
    "rating": 4.5,
    "price_range": "$$$$",
    "google_maps_url": "https://maps.google.com/...",
    "is_starred": false
  }
]
```

**Error (400):** Activity missing coordinates
```json
{
  "detail": "Activity location missing coordinates. Please geocode first."
}
```

---

#### Star/Unstar Place

```http
PUT /api/trip/{trip_id}/activities/{activity_id}/discover/{place_type}/{place_id}/star?starred=true
```

**Response:** Updated `DiscoveredPlace`

---

#### Get All Discoveries for Trip

```http
GET /api/trip/{trip_id}/discoveries
```

**Response:**
```json
[
  {
    "trip_id": "trip_123",
    "activity_id": "act_1",
    "discovery_type": "restaurant",
    "places": [...]
  }
]
```

---

#### Delete Discovery

```http
DELETE /api/trip/{trip_id}/activities/{activity_id}/discover/{place_type}
```

**Response:** `204 No Content`

---

### Admin

#### Cleanup Expired Sessions

```http
POST /api/trip/sessions/cleanup
```

**Response:**
```json
{
  "message": "Cleaned up 5 expired sessions"
}
```

---

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error message here"
}
```

| Status Code | Meaning |
|-------------|---------|
| 400 | Bad Request (validation error) |
| 404 | Resource not found |
| 500 | Internal server error |

## Validation Rules

| Field | Rules |
|-------|-------|
| `destinations` | At least 1 destination required |
| `budget_limit` | Must be positive |
| `start_date` | Must be in the future |
| `end_date` | Must be after start_date |

