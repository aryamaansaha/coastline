# Frontend Architecture

System design, component hierarchy, and data flow.

## High-Level Overview

```mermaid
graph TB
    subgraph Frontend["Frontend (React + Vite)"]
        App[App.tsx<br/>Router]
        Context[TripContext<br/>Global State]
        Hooks[Custom Hooks<br/>useTripStream, useApi]
        Pages[Pages<br/>Landing, Loading, Review, Trip]
        Components[Components<br/>Reusable UI]
    end
    
    subgraph Backend["Backend (FastAPI)"]
        API[REST API]
        SSE[SSE Stream]
    end
    
    App --> Pages
    Pages --> Components
    Pages --> Hooks
    Hooks --> Context
    Hooks --> API
    Hooks --> SSE
    Context --> Pages
```

## Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| Framework | React 19 | UI components |
| Build | Vite 7 | Dev server, bundling |
| Language | TypeScript 5.9 | Type safety |
| Routing | React Router v7 | Client-side navigation |
| State | React Context | Global state management |
| Styling | CSS Modules | Scoped component styles |
| Icons | Lucide React | SVG icon library |
| Maps | Leaflet + react-leaflet | Interactive maps |
| SSE | @microsoft/fetch-event-source | Robust SSE client |
| Dates | date-fns | Date formatting |

## Component Hierarchy

```mermaid
graph TD
    App["App.tsx"]
    App --> BrowserRouter
    BrowserRouter --> Routes
    
    Routes --> TripsListPage["/ → TripsListPage"]
    Routes --> PlanningFlow["/new → PlanningFlow"]
    Routes --> TripPage["/trip → TripPage"]
    
    PlanningFlow --> LandingPage
    PlanningFlow --> LoadingPage
    PlanningFlow --> ReviewPage
    
    LandingPage --> Logo
    LoadingPage --> Logo
    
    ReviewPage --> DaySection
    ReviewPage --> BudgetBar
    ReviewPage --> TripMap
    ReviewPage --> RevisionModal
    
    TripPage --> DaySection
    TripPage --> BudgetBar
    TripPage --> TripMap
    TripPage --> DiscoveryDrawer
    
    DaySection --> ActivityCard
    
    TripsListPage --> Logo
    TripsListPage --> ConfirmModal
```

## Data Flow

```mermaid
sequenceDiagram
    participant User
    participant UI as React UI
    participant Context as TripContext
    participant Hook as useTripStream
    participant API as Backend API
    participant SSE as SSE Stream
    
    User->>UI: Fill form & submit
    UI->>Hook: startGeneration(prefs)
    Hook->>Context: setIsStreaming(true)
    Hook->>SSE: POST /api/trip/generate/stream
    
    loop Agent Processing
        SSE-->>Hook: Event: planning/searching
        Hook->>Context: setStreamStatus(msg)
        Context-->>UI: Re-render LoadingPage
    end
    
    SSE-->>Hook: Event: awaiting_approval
    Hook->>Context: setPreview(data)
    Hook->>Context: setIsStreaming(false)
    Context-->>UI: Render ReviewPage
    
    User->>UI: Click Approve
    UI->>Hook: submitDecision('approve')
    Hook->>SSE: POST /session/:id/decide
    
    SSE-->>Hook: Event: complete
    Hook->>Context: setFinalTripId(id)
    Context-->>UI: Navigate to TripPage
```

## State Architecture

### Global State (TripContext)

```typescript
interface TripContextType {
  // User Input
  preferences: TripPreferences | null;
  
  // Session Management
  sessionId: string | null;
  
  // SSE State
  isStreaming: boolean;
  streamStatus: string;
  streamError: string | null;
  
  // HITL State
  preview: TripPreview | null;
  
  // Completion
  finalTripId: string | null;
  
  // Persistence
  startedAt: number | null;
  activeSession: ActiveSession | null;
  hasActiveSession: boolean;
  
  // Actions
  resetTrip: () => void;
  restoreSession: () => ActiveSession | null;
}
```

### State Transitions

```mermaid
stateDiagram-v2
    [*] --> Idle: Initial
    Idle --> Streaming: startGeneration()
    Streaming --> AwaitingApproval: awaiting_approval event
    AwaitingApproval --> Streaming: submitDecision('revise')
    AwaitingApproval --> Complete: submitDecision('approve')
    Complete --> [*]: resetTrip()
    
    Streaming --> Error: error event
    AwaitingApproval --> Idle: cancel
    Error --> Idle: resetTrip()
```

## Routing Architecture

| Route | Component | Purpose |
|-------|-----------|---------|
| `/` | TripsListPage | List saved trips, in-progress banner |
| `/new` | PlanningFlow | Dynamic: Landing → Loading → Review |
| `/trip?id=...` | TripPage | View saved trip with discovery |

### PlanningFlow Logic

```mermaid
graph TD
    PlanningFlow{State Check}
    PlanningFlow -->|finalTripId| Redirect[Navigate to /trip]
    PlanningFlow -->|streamError| ErrorView[Error UI]
    PlanningFlow -->|preview| ReviewPage
    PlanningFlow -->|isStreaming OR hasActiveSession| LoadingPage
    PlanningFlow -->|default| LandingPage
```

## Styling Architecture

### CSS Modules Pattern

Each component has a paired `.module.css` file:

```
components/
├── ActivityCard.tsx
├── ActivityCard.module.css
├── BudgetBar.tsx
├── BudgetBar.module.css
```

### Global Variables (index.css)

```css
:root {
  --primary: #0f172a;
  --primary-light: #e0f2fe;
  --text: #0f172a;
  --text-muted: #64748b;
  --bg: #f8fafc;
  --surface: #ffffff;
  --border: #e2e8f0;
}
```

### Design Principles

1. **Split-screen layout** for review/trip pages (itinerary | map)
2. **Cards** for trip listings and activities
3. **Soft shadows and rounded corners** for modern feel
4. **Blue accent color** for primary actions
5. **Responsive padding and spacing**

## API Communication

### REST API (useApi hook)

```typescript
// Trip operations
useTrips(): { getTrip, listTrips, deleteTrip }

// Discovery operations  
useDiscovery(): { discoverPlaces, starPlace, getAllDiscoveries }
```

### SSE Streaming (useTripStream hook)

```typescript
useTripStream(): {
  startGeneration,  // POST /api/trip/generate/stream
  submitDecision,   // POST /api/trip/session/:id/decide
  reconnectSession, // GET /api/trip/session/:id/status
  cancelStream      // Abort controller
}
```

## Key Patterns

### 1. Context + Hooks Separation

- **Context**: Holds state, provides setters
- **Hooks**: Contain logic, call APIs, update context

### 2. Optimistic Updates

- Navigate immediately after approve
- Geocoding happens in background
- Poll for status updates

### 3. Session Persistence

- Save to localStorage on state changes
- Restore on page reload
- 30-minute expiration

### 4. Discovery Caching

- Cache by activity ID + type
- Persist across drawer open/close
- Refresh on demand

## Error Handling

| Error Type | Handling |
|------------|----------|
| SSE Connection Failed | Show error UI, allow retry |
| API 422 (Validation) | Parse details, display message |
| API 404 (Not Found) | Clear session, show not found |
| Network Error | Show generic error, allow retry |

## Performance Considerations

1. **Memoization**: `useMemo` for computed values
2. **Callbacks**: `useCallback` for stable references
3. **Refs**: Track active connections, prevent duplicates
4. **Lazy loading**: Pages loaded on route access
5. **Debounced polling**: 2-second intervals for geocoding

