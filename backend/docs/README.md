# Coastline Backend Documentation

AI-powered travel planning with Human-in-the-Loop (HITL) workflow.

## Documentation Index

| Document | Description |
|----------|-------------|
| [QUICKSTART.md](./QUICKSTART.md) | Setup guide, installation, running the server |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | System design, component interactions, data flow |
| [AGENT_GRAPH.md](./AGENT_GRAPH.md) | LangGraph agent flow, state management, nodes |
| [MCP_SERVER.md](./MCP_SERVER.md) | MCP protocol, Amadeus tools, retry logic |
| [API.md](./API.md) | REST API reference, endpoints, request/response |
| [SSE.md](./SSE.md) | Server-Sent Events, streaming, client implementation |

## Quick Links

### Starting Point
→ New to the project? Start with [QUICKSTART.md](./QUICKSTART.md)

### Understanding the System
→ How does it all work? See [ARCHITECTURE.md](./ARCHITECTURE.md)

### Frontend Integration
→ Building the UI? Check [API.md](./API.md) and [SSE.md](./SSE.md)

### Agent Development
→ Modifying the AI? Read [AGENT_GRAPH.md](./AGENT_GRAPH.md)

## Tech Stack

- **Framework:** FastAPI
- **Agent:** LangGraph
- **Database:** MongoDB
- **LLM:** OpenAI / Anthropic / Google (configurable)
- **Travel API:** Amadeus
- **Discovery:** Google Gemini with Maps grounding
- **Geocoding:** Nominatim OpenStreetMap

