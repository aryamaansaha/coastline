# Quick Start Guide

## Prerequisites

- Python 3.12+
- MongoDB running locally (or remote URI)
- API keys for:
  - OpenAI / Anthropic / Google (LLM provider)
  - Amadeus (flight/hotel search)
  - Google AI Studio (place discovery)

## Installation

```bash
# Clone and navigate
cd coastline/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt
```

## Environment Setup

Create `.env` file in the `backend/` directory:

**Note:** The `.env` file should be located in the `backend/` folder. The `load_dotenv()` function will automatically find it when the FastAPI app starts.

```bash
# Backend Configuration
BACKEND_PORT=8008            # Port for FastAPI server (default: 8008)

# Database
MONGODB_URI=mongodb://localhost:27017/

# LLM Provider (choose one)
LLM_PROVIDER=openai          # or: anthropic, google
LLM_MODEL=gpt-4o             # or: claude-sonnet-4-20250514, gemini-2.0-flash
LLM_TEMPERATURE=0.3

# API Keys (based on provider)
OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...
# GOOGLE_API_KEY=...

# Amadeus (required)
AMADEUS_API_KEY=your_key
AMADEUS_API_SECRET=your_secret

# Google AI Studio (for discovery)
GOOGLE_API_KEY=your_key
```

## Running the Server

```bash
# Start FastAPI server (uses BACKEND_PORT from .env, defaults to 8008)
uvicorn app.main:app --reload --port ${BACKEND_PORT:-8008}

# Or set the port explicitly
BACKEND_PORT=8008 uvicorn app.main:app --reload --port 8008
```

**Note:** 
- The frontend Vite proxy and test scripts will automatically use the `BACKEND_PORT` environment variable
- Make sure to set `BACKEND_PORT` in your `.env` file or export it before running the frontend or tests
- For the frontend, you can also set it when running: `BACKEND_PORT=8008 npm run dev`

## Testing the API

### Generate a Trip

```bash
curl -X POST http://localhost:8008/api/trip/generate/stream \
  -H "Content-Type: application/json" \
  -d '{
    "destinations": ["Paris"],
    "start_date": "2025-03-15T00:00:00Z",
    "end_date": "2025-03-18T00:00:00Z",
    "budget_limit": 2000,
    "origin": "New York"
  }'
```

### Interactive Testing

```bash
# Run interactive HITL test
python test_interactive.py
```

This provides a CLI interface to:
1. Enter trip preferences
2. Review generated itinerary
3. Approve, revise with feedback, or cancel
4. See the full HITL flow in action

### List Trips

```bash
curl http://localhost:8008/api/trips
```

### Get Trip Details

```bash
curl http://localhost:8008/api/trip/{trip_id}
```

## Project Structure

```
backend/
├── app/
│   ├── main.py           # FastAPI app entry point
│   ├── database.py       # MongoDB connection
│   ├── prompts.py        # LLM prompt templates
│   ├── routers/
│   │   ├── session.py    # SSE streaming, HITL endpoints
│   │   ├── trip.py       # Trip CRUD
│   │   └── discovery.py  # Place discovery
│   ├── schemas/          # Pydantic models
│   └── services/         # Business logic
├── mcp/
│   └── server.py         # Amadeus API tools
├── agent_graph_v3.py     # LangGraph agent
├── docs/                 # Documentation
└── requirements.txt
```

## Key Flows

### Trip Generation

1. Client POSTs preferences to `/api/trip/generate/stream`
2. Server streams SSE events (searching, planning, validating)
3. When ready, server sends `awaiting_approval` with itinerary preview
4. Client displays UI for user to approve/revise
5. Client POSTs decision to `/api/trip/session/{id}/decide`
6. On approve: trip saved, `complete` event sent
7. On revise: agent continues with feedback

### Place Discovery

1. After trip is saved, client can discover places near activities
2. POST to `/api/trip/{id}/activities/{id}/discover/restaurant`
3. Server uses Gemini with Google Maps grounding
4. Returns nearby places with ratings, addresses, map URLs
5. User can star favorites

## Troubleshooting

### MongoDB Connection

```bash
# Check MongoDB is running
mongosh --eval "db.adminCommand('ping')"
```

### Missing API Keys

Check `.env` file and ensure keys are exported:
```bash
source .env  # or use python-dotenv
```

### Rate Limits

Amadeus API has rate limits. The server includes retry logic with exponential backoff (max 3 attempts).

### LLM Errors

Check `backend/logs/` for saved LLM responses and parse errors when debugging JSON issues.

## Next Steps

- See [ARCHITECTURE.md](./ARCHITECTURE.md) for system design
- See [AGENT_GRAPH.md](./AGENT_GRAPH.md) for agent details
- See [API.md](./API.md) for full API reference
- See [SSE.md](./SSE.md) for streaming implementation

