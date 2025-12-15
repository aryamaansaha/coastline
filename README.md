# 🌊 Coastline

**AI-powered travel planning with human-in-the-loop refinement.**

Coastline generates personalized multi-city itineraries using AI agents, letting you review, revise, and approve before finalizing. Discover nearby restaurants, bars, and cafes for each activity with Google Maps integration.

---

## ✨ Features

- **AI Itinerary Generation** — Multi-day, multi-city trip planning with budget awareness
- **Human-in-the-Loop** — Review AI drafts, request revisions, approve when satisfied
- **Real-time Streaming** — Watch your itinerary build in real-time via SSE
- **Place Discovery** — Find nearby restaurants, bars, and cafes for any activity
- **Interactive Maps** — Leaflet-powered maps with activity markers
- **Mobile Responsive** — Full mobile support with optimized touch interactions
- **Session Persistence** — Resume in-progress trips across browser sessions

---

## 🚀 Quick Start

### Prerequisites

- Node.js 18+
- Python 3.12+
- MongoDB (local or Docker)
- API Keys: OpenAI/Anthropic, Google Gemini, Amadeus

### Using Docker (Recommended)

```bash
# Clone the repo
git clone https://github.com/yourusername/coastline.git
cd coastline

# Copy environment file and add your API keys
cp .env.example .env

# Start all services
docker-compose up --build
```


### Local Development

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8008

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

Access at **http://localhost:5173**

---

## 🏗️ Architecture

```
┌─────────────┐     SSE      ┌─────────────┐     MCP      ┌─────────────┐
│   Frontend  │◄────────────►│   Backend   │◄────────────►│   Amadeus   │
│   (React)   │              │  (FastAPI)  │              │    API      │
└─────────────┘              └──────┬──────┘              └─────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
              ┌─────▼─────┐   ┌─────▼─────┐   ┌─────▼─────┐
              │  MongoDB  │   │ LangGraph │   │  Gemini   │
              │           │   │   Agent   │   │ Discovery │
              └───────────┘   └───────────┘   └───────────┘
```

---

## 📁 Project Structure

```
coastline/
├── backend/               # FastAPI backend
│   ├── app/
│   │   ├── main.py        # Entry point
│   │   ├── routers/       # API endpoints
│   │   ├── services/      # Business logic
│   │   └── schemas/       # Pydantic models
│   ├── mcp/               # MCP server (Amadeus)
│   └── docs/              # Backend documentation
│
├── frontend/              # React frontend
│   ├── src/
│   │   ├── pages/         # Route pages
│   │   ├── components/    # Reusable UI
│   │   ├── hooks/         # Custom hooks
│   │   └── context/       # React context
│   └── docs/              # Frontend documentation
│
└── docker-compose.yaml    # Container orchestration
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React, TypeScript, Vite, Leaflet |
| Backend | FastAPI, LangGraph, Pydantic |
| Database | MongoDB |
| AI/LLM | OpenAI / Anthropic / Google Gemini |
| Travel Data | Amadeus API (via MCP) |
| Geocoding | Nominatim (OpenStreetMap) |

---

## 📖 Documentation

| Area | Link |
|------|------|
| Backend Setup | [backend/docs/QUICKSTART.md](./backend/docs/QUICKSTART.md) |
| Frontend Setup | [frontend/docs/QUICKSTART.md](./frontend/docs/QUICKSTART.md) |
| API Reference | [backend/docs/API.md](./backend/docs/API.md) |
| Agent Architecture | [backend/docs/AGENT_GRAPH.md](./backend/docs/AGENT_GRAPH.md) |

---

## 🔑 Environment Variables

```env
# LLM (pick one or more)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...

# Travel API
AMADEUS_API_KEY=...
AMADEUS_API_SECRET=...

# Database
MONGODB_URI=mongodb://localhost:27017/
```

See `.env.example` for full configuration.

---
