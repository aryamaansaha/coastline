# Types

TypeScript interfaces and domain models.

## Overview

All TypeScript types are centralized in `src/types/index.ts` and mirror the backend Pydantic schemas.

## Domain Models

### Location

```typescript
export interface Location {
  name: string;      // Place name (e.g., "Big Ben")
  address: string;   // Street address
  lat?: number | null;
  lng?: number | null;
}
```

### Activity

```typescript
export interface Activity {
  id: string;
  type: 'flight' | 'hotel' | 'activity';
  time_slot: string;           // e.g., "09:00 AM"
  title: string;
  description: string;
  activity_suggestion?: string;
  location: Location;
  estimated_cost: number;
  price_suggestion?: string;
  currency: string;
}
```

### Day

```typescript
export interface Day {
  id?: string;
  day_number: number;
  theme: string;       // e.g., "London Arrival Day"
  city: string;
  activities: Activity[];
}
```

### GeocodingStatus

```typescript
export interface GeocodingStatus {
  status: 'pending' | 'in_progress' | 'complete' | 'failed';
  total_activities: number;
  geocoded_activities: number;
}
```

### Itinerary

```typescript
export interface Itinerary {
  trip_id: string;
  trip_title: string;
  days: Day[];
  budget_limit: number;
  total_cost?: number;
  created_at?: string;
  updated_at?: string;
  geocoding_status?: GeocodingStatus | null;
}
```

## Cost Types

### CostBreakdown

```typescript
export interface CostBreakdown {
  flights: number;
  hotels: number;
  activities: number;
}
```

## SSE / Agent Types

### SSEEventType

```typescript
export type SSEEventType = 
  | 'starting'
  | 'searching'
  | 'planning'
  | 'validating'
  | 'awaiting_approval'
  | 'complete'
  | 'error';
```

### SSEEventData

```typescript
export interface SSEEventData {
  message?: string;
  session_id?: string;
  status?: string;
  preview?: TripPreview;
  trip_id?: string;
}
```

### TripPreview

```typescript
export interface TripPreview {
  itinerary: Itinerary;
  total_cost: number;
  cost_breakdown: CostBreakdown;
  budget_limit: number;
  budget_status: 'under' | 'over' | 'unknown';
  revision_count: number;
}
```

## User Input Types

### TripPreferences

```typescript
export interface TripPreferences {
  destinations: string[];
  start_date: string;    // ISO string
  end_date: string;      // ISO string
  budget_limit: number;
  origin: string;
}
```

## Trip Summary (List View)

### TripSummary

```typescript
export interface TripSummary {
  trip_id: string;
  trip_title: string;
  budget_limit: number;
  destinations: string[];
  num_days: number;
  created_at: string | null;
  updated_at: string | null;
}
```

## Discovery Types

### DiscoveryType

```typescript
export type DiscoveryType = 'restaurant' | 'bar' | 'cafe' | 'club';
```

### DiscoveredPlace

```typescript
export interface DiscoveredPlace {
  id: string;
  place_type: DiscoveryType;
  name: string;
  address: string;
  rating?: number | null;
  price_range?: string | null;
  google_maps_url: string;
  lat: number;
  lng: number;
  starred: boolean;
  extra_data?: Record<string, unknown>;
}
```

## Session Types

### SessionStatus

```typescript
export type SessionStatus = 
  | 'processing'
  | 'awaiting_approval'
  | 'complete'
  | 'failed';
```

### HumanDecision

```typescript
export interface HumanDecision {
  action: 'approve' | 'revise';
  feedback?: string;
  new_budget?: number;
}
```

## Context Types

### ActiveSession (sessionStorage)

```typescript
// Defined in utils/sessionStorage.ts
export interface ActiveSession {
  sessionId: string;
  preferences: TripPreferences;
  startedAt: number;  // Unix timestamp
  status: 'generating' | 'awaiting_approval' | 'finalizing';
  tripTitle?: string;
}
```

### TripContextType

```typescript
// Defined in context/TripContext.tsx
interface TripContextType {
  preferences: TripPreferences | null;
  setPreferences: (prefs: TripPreferences) => void;
  
  sessionId: string | null;
  setSessionId: (id: string | null) => void;
  
  isStreaming: boolean;
  setIsStreaming: (streaming: boolean) => void;
  streamStatus: string;
  setStreamStatus: (status: string) => void;
  streamError: string | null;
  setStreamError: (err: string | null) => void;
  
  preview: TripPreview | null;
  setPreview: (preview: TripPreview | null) => void;
  
  finalTripId: string | null;
  setFinalTripId: (id: string | null) => void;

  startedAt: number | null;
  setStartedAt: (time: number | null) => void;
  activeSession: ActiveSession | null;
  hasActiveSession: boolean;
  
  resetTrip: () => void;
  restoreSession: () => ActiveSession | null;
}
```

## Hook Return Types

### useTrips

```typescript
{
  getTrip: (tripId: string) => Promise<Itinerary | null>;
  listTrips: () => Promise<TripSummary[]>;
  deleteTrip: (tripId: string) => Promise<boolean>;
  loading: boolean;
  error: string | null;
}
```

### useDiscovery

```typescript
{
  discoverPlaces: (tripId: string, activityId: string, type: DiscoveryType, regenerate?: boolean) => Promise<DiscoveredPlace[]>;
  starPlace: (tripId: string, activityId: string, type: DiscoveryType, placeId: string, starred: boolean) => Promise<DiscoveredPlace | null>;
  getAllDiscoveries: (tripId: string) => Promise<DiscoveryResponse[]>;
  loading: boolean;
  error: string | null;
}
```

### useTripStream

```typescript
{
  startGeneration: (prefs: TripPreferences) => Promise<void>;
  submitDecision: (action: 'approve' | 'revise', feedback?: string, newBudget?: number) => Promise<void>;
  reconnectSession: (sessionId: string, prefs: TripPreferences, startedAt: number) => Promise<void>;
  cancelStream: () => void;
}
```

## Type Guards

### Optional: Type narrowing helpers

```typescript
// Example usage
function isActivity(item: Activity | Day): item is Activity {
  return 'time_slot' in item;
}

function hasCoordinates(location: Location): location is Location & { lat: number; lng: number } {
  return location.lat != null && location.lng != null;
}
```

## Backend Schema Mapping

| Frontend Type | Backend Schema |
|---------------|----------------|
| `TripPreferences` | `Preferences` |
| `Itinerary` | `Itinerary` |
| `Day` | `Day` |
| `Activity` | `Activity` |
| `Location` | `Location` |
| `TripPreview` | `SessionPreview` |
| `DiscoveredPlace` | `DiscoveredPlace` |
| `HumanDecision` | `HumanDecision` |

## Import Pattern

```typescript
import type { 
  Activity, 
  Day, 
  Itinerary, 
  TripPreferences,
  DiscoveredPlace,
  DiscoveryType 
} from '../types';
```

Using `import type` ensures types are stripped at build time.

## Related

- [Backend API Schemas](../../backend/docs/API.md)
- [STATE_MANAGEMENT.md](./STATE_MANAGEMENT.md) - Context types usage
- [COMPONENTS.md](./COMPONENTS.md) - Props interfaces

