# Coastline

AI-powered travel planner with smart place discovery using Gemini + Google Maps.

---

## Quick Start

```bash
# 1. Start MongoDB
docker run -d --name mongodb -p 27017:27017 mongo

# 2. Setup backend
cd backend
pip install -r requirements.txt
cp .env.example .env  # Add your GOOGLE_API_KEY

# 3. Run server
uvicorn app.main:app --reload --port 8008

# 4. Test API
curl http://localhost:8008/docs  # Swagger UI
```

---

## Documentation

- **[API_REFERENCE.md](./API_REFERENCE.md)** - Complete API reference (endpoints, models, examples)
- **[HIGH-LEVEL.md](./HIGH-LEVEL.md)** - System architecture & tech stack

---

## Project Structure

```
coastline/
├── backend/          # FastAPI server
│   ├── app/
│   │   ├── routers/      # API endpoints
│   │   ├── services/     # Business logic
│   │   ├── schemas/      # Pydantic models
│   │   └── database.py   # MongoDB connection
│   └── requirements.txt
├── frontend/         # React (TODO)
└── API_REFERENCE.md           # API documentation
```

---

## Core Features

- **Trip Generation** - Agent creates day-by-day itineraries (mock data for MVP)
- **Smart Discovery** - Find restaurants, bars, cafes near activities using Gemini + Google Maps
- **Caching** - First discovery calls Gemini (~2s), subsequent from MongoDB (~20ms)
- **Starring** - Mark favorites that persist across regenerations
- **Regeneration** - Refresh suggestions while keeping starred places

---

## Tech Stack

- **Backend:** FastAPI, Python 3.12
- **Database:** MongoDB (itineraries + discoveries)
- **AI:** Gemini 2.5 Flash (with Google Maps grounding)
- **Geocoding:** Nominatim (OpenStreetMap)
- **Agent:** LangGraph (planned)
- **Frontend:** React+Vite (planned)

---

## Development Status

✅ **Completed:**
- Trip CRUD with MongoDB persistence
- Generic discovery pattern (restaurants, bars, cafes, clubs, shopping, attractions)
- Gemini + Google Maps integration
- Starring and regeneration features
- Caching and performance optimization

⏳ **In Progress:**
- LangGraph agent for trip generation
- Frontend UI
- User authentication

⏳ **Planned:**
- MCP tools for flights/hotels
- Graphiti for user preference memory
- Collaborative trip planning
- Map visualization

---

## Contributing

When adding new features:
1. Update Pydantic schemas in `app/schemas/`
2. Add business logic in `app/services/`
3. Create routes in `app/routers/`
4. Update `API_REFERENCE.md` with new endpoints
5. Test with Swagger UI at `/docs`

---

