# System Architecture

## Overview

Coastline is an AI-powered travel planning application with a Human-in-the-Loop (HITL) workflow. The system generates multi-city itineraries using LLM agents, validates costs against user budgets, and allows iterative refinement based on user feedback.

## High-Level Architecture

```mermaid
flowchart TB
    subgraph Client["Frontend (Future)"]
        UI[Web UI]
    end

    subgraph Backend["FastAPI Backend"]
        API[API Layer]
        SSE[SSE Streaming]
        
        subgraph Services
            SessionSvc[Session Service]
            TripSvc[Trip Service]
            DiscoverySvc[Discovery Service]
            GeoSvc[Geocode Service]
            LLMSvc[LLM Provider]
        end
        
        subgraph Agent["LangGraph Agent"]
            Planner[Planner Node]
            Tools[Tool Executor]
            Auditor[Auditor Node]
            Review[Human Review Node]
        end
    end

    subgraph External["External Services"]
        MCP[MCP Server]
        Amadeus[Amadeus API]
        Nominatim[Nominatim OSM]
        Gemini[Google Gemini]
        LLM[LLM Provider]
    end

    subgraph Storage["Data Layer"]
        MongoDB[(MongoDB)]
    end

    UI --> API
    API --> SSE
    SSE --> SessionSvc
    SessionSvc --> Agent
    Agent --> MCP
    MCP --> Amadeus
    Agent --> LLM
    GeoSvc --> Nominatim
    DiscoverySvc --> Gemini
    Services --> MongoDB
```

## Component Overview

| Component | Purpose | Key Files |
|-----------|---------|-----------|
| **API Layer** | HTTP endpoints, request validation | `app/routers/` |
| **Session Service** | HITL session management, state persistence | `app/services/session.py` |
| **LangGraph Agent** | Trip planning, tool orchestration | `agent_graph_v3.py` |
| **MCP Server** | Amadeus API integration, cost calculation | `mcp/server.py` |
| **Discovery Service** | Nearby places (restaurants, bars, etc.) | `app/services/discovery.py` |
| **Geocode Service** | Address → coordinates conversion | `app/services/geocode.py` |

## Data Flow

### Trip Generation Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant API as FastAPI
    participant Sess as Session Service
    participant Agent as LangGraph Agent
    participant MCP as MCP Server
    participant DB as MongoDB

    C->>API: POST /api/trip/generate/stream
    API->>Sess: Create session
    Sess->>DB: Store session
    API-->>C: SSE stream opened

    loop Planning Loop
        Agent->>MCP: Search flights/hotels
        MCP-->>Agent: Results
        Agent->>Agent: Generate itinerary
        Agent->>Agent: Auditor validates
        
        alt Over Budget
            Agent->>Agent: Request revision
        else Valid
            Agent->>Sess: Update state (interrupt)
            Sess-->>C: SSE: awaiting_approval
        end
    end

    C->>API: POST /session/{id}/decide
    
    alt Approve
        Agent->>DB: Save itinerary
        Sess-->>C: SSE: complete
    else Revise
        Agent->>Agent: Continue with feedback
    end
```

## Database Schema

```mermaid
erDiagram
    ITINERARIES {
        string trip_id PK
        string trip_title
        float budget_limit
        array days
        datetime created_at
        datetime updated_at
    }
    
    SESSIONS {
        string session_id PK
        string status
        dict preferences
        dict human_decision
        datetime created_at
        datetime expires_at
    }
    
    AGENT_CHECKPOINTS {
        string thread_id PK
        string checkpoint_id PK
        bytes data
        datetime updated_at
    }
    
    DISCOVERIES {
        string trip_id FK
        string activity_id
        string discovery_type
        array places
    }

    ITINERARIES ||--o{ DISCOVERIES : "has"
```

## Key Design Decisions

1. **SSE over WebSockets** - Simpler implementation, sufficient for one-way streaming
2. **MongoDB Checkpointer** - Persists agent state for interrupt/resume capability
3. **MCP Protocol** - Standardized tool interface, separation of concerns
4. **LLM Provider Abstraction** - Easy switching between OpenAI/Anthropic/Google
5. **Geocoding Post-Processing** - LLM generates addresses, backend geocodes for coordinates

