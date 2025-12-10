# Frontend Quickstart

Get the Coastline frontend running locally.

## Prerequisites

- Node.js 18+ (LTS recommended)
- npm 9+
- Backend server running on port 8008

## Installation

```bash
# From repository root
cd frontend

# Install dependencies
npm install
```

## Development Server

```bash
npm run dev
```

Opens at **http://localhost:5173**

The Vite dev server automatically proxies `/api/*` requests to the backend at `localhost:8008`.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BACKEND_PORT` | `8008` | Backend API port for proxy |

To customize:

```bash
BACKEND_PORT=8000 npm run dev
```

## Project Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start development server with HMR |
| `npm run build` | Build for production |
| `npm run preview` | Preview production build |
| `npm run lint` | Run ESLint |

## Production Build

```bash
npm run build
```

Output goes to `dist/` folder. Serve with any static file server.

```bash
npm run preview  # Preview locally
```

## Proxy Configuration

Vite proxies all `/api/*` requests to the backend:

```typescript
// vite.config.ts
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8008',
      changeOrigin: true,
      secure: false,
    }
  }
}
```

## Development Workflow

### 1. Start Backend First

```bash
cd backend
uvicorn app.main:app --port 8008 --reload
```

### 2. Start Frontend

```bash
cd frontend
npm run dev
```

### 3. Open Browser

Navigate to http://localhost:5173

## File Structure Overview

```
src/
├── App.tsx              # Root component + routing
├── main.tsx             # Entry point, TripProvider
├── index.css            # Global styles
├── context/
│   └── TripContext.tsx  # Global state management
├── hooks/
│   ├── useTripStream.ts # SSE connection
│   └── useApi.ts        # API helpers
├── pages/
│   ├── LandingPage.tsx  # Trip form
│   ├── LoadingPage.tsx  # Agent progress
│   ├── ReviewPage.tsx   # HITL review
│   ├── TripPage.tsx     # Saved trip view
│   └── TripsListPage.tsx# My trips list
├── components/          # Reusable components
├── types/
│   └── index.ts         # TypeScript interfaces
└── utils/
    └── sessionStorage.ts# Session persistence
```

## Common Issues

### "Failed to connect" Error

Backend not running. Start it first:

```bash
cd backend && uvicorn app.main:app --port 8008
```

### Blank Page / Console Errors

Check browser console for TypeScript/import errors. Run `npm run lint` to find issues.

### Map Not Loading

Leaflet CSS not imported. Verify `leaflet/dist/leaflet.css` is imported in `TripMap.tsx`.

### SSE Connection Drops

Check network tab for failed `/api/trip/generate/stream` requests. Backend may have crashed.

## Next Steps

- Read [ARCHITECTURE.md](./ARCHITECTURE.md) for system overview
- Read [STATE_MANAGEMENT.md](./STATE_MANAGEMENT.md) for data flow
- Read [SSE_INTEGRATION.md](./SSE_INTEGRATION.md) for real-time updates

