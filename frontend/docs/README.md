# Coastline Frontend Documentation

React-based travel planning UI with real-time SSE streaming and Human-in-the-Loop workflow.

## Documentation Index

| Document | Description |
|----------|-------------|
| [QUICKSTART.md](./QUICKSTART.md) | Setup guide, development server, environment |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | System design, component hierarchy, data flow |
| [STATE_MANAGEMENT.md](./STATE_MANAGEMENT.md) | TripContext, state patterns, session persistence |
| [ROUTING.md](./ROUTING.md) | Routes, navigation, PlanningFlow logic |
| [SSE_INTEGRATION.md](./SSE_INTEGRATION.md) | Server-Sent Events, useTripStream hook |
| [SESSION_PERSISTENCE.md](./SESSION_PERSISTENCE.md) | Background generation, localStorage, reconnection |
| [PAGES.md](./PAGES.md) | Page components, user flows, state dependencies |
| [COMPONENTS.md](./COMPONENTS.md) | Reusable components, props, styling |
| [DISCOVERY.md](./DISCOVERY.md) | Place discovery, drawer, caching strategy |
| [TYPES.md](./TYPES.md) | TypeScript interfaces, domain models |

## Quick Links

### Starting Point
→ New to the project? Start with [QUICKSTART.md](./QUICKSTART.md)

### Understanding the System
→ How does it all work? See [ARCHITECTURE.md](./ARCHITECTURE.md)

### State & Data Flow
→ Managing state? Read [STATE_MANAGEMENT.md](./STATE_MANAGEMENT.md)

### SSE & Real-time
→ Streaming updates? Check [SSE_INTEGRATION.md](./SSE_INTEGRATION.md)

## Tech Stack

- **Framework:** React 19
- **Build Tool:** Vite 7
- **Language:** TypeScript 5.9
- **Routing:** React Router v7
- **State:** React Context + Hooks
- **Styling:** CSS Modules
- **Icons:** Lucide React
- **Maps:** Leaflet + react-leaflet
- **SSE Client:** @microsoft/fetch-event-source

## Project Structure

```
frontend/
├── src/
│   ├── components/     # Reusable UI components
│   ├── context/        # React Context (TripContext)
│   ├── hooks/          # Custom hooks (useTripStream, useApi)
│   ├── pages/          # Page components
│   ├── types/          # TypeScript type definitions
│   ├── utils/          # Utility functions
│   ├── assets/         # Static assets (images, logos)
│   ├── App.tsx         # Root component + routing
│   └── main.tsx        # Entry point
├── docs/               # This documentation
├── public/             # Public static files
└── vite.config.ts      # Vite configuration
```

## Related Documentation

- [Backend API Reference](../../backend/docs/API.md)
- [Backend SSE Events](../../backend/docs/SSE.md)
- [Backend Architecture](../../backend/docs/ARCHITECTURE.md)

