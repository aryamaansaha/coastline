// === Domain Models ===

export interface Location {
  name: string;
  address: string;
  lat?: number | null;
  lng?: number | null;
}

export interface Activity {
  id: string;
  type: 'flight' | 'hotel' | 'activity';
  time_slot: string;
  title: string;
  description: string;
  activity_suggestion?: string;
  location: Location;
  estimated_cost: number;
  price_suggestion?: string;
  currency: string;
}

export interface Day {
  id?: string;
  day_number: number;
  theme: string;
  city: string;
  activities: Activity[];
}

export interface Itinerary {
  trip_id: string;
  trip_title: string;
  days: Day[];
  budget_limit: number;
  total_cost?: number;
  created_at?: string;
  updated_at?: string;
}

// === Cost ===

export interface CostBreakdown {
  flights: number;
  hotels: number;
  activities: number;
}

// === SSE / Agent Types ===

export type SSEEventType = 
  | 'starting'
  | 'searching'
  | 'planning'
  | 'validating'
  | 'awaiting_approval'
  | 'complete'
  | 'error';

export interface SSEEventData {
  message?: string;
  session_id?: string;
  status?: string;
  preview?: TripPreview;
  trip_id?: string;
}

export interface TripPreview {
  itinerary: Itinerary;
  total_cost: number;
  cost_breakdown: CostBreakdown;
  budget_limit: number;
  budget_status: 'under' | 'over' | 'unknown';
  revision_count: number;
}

// === Preferences ===

export interface TripPreferences {
  destinations: string[];
  start_date: string;
  end_date: string;
  budget_limit: number;
  origin: string;
}

// === Trip Summary (for listing) ===

export interface TripSummary {
  trip_id: string;
  trip_title: string;
  budget_limit: number;
  destinations: string[];
  num_days: number;
  created_at: string | null;
  updated_at: string | null;
}

// === Discovery Types ===

export type DiscoveryType = 'restaurant' | 'bar' | 'cafe' | 'club';

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

// === Session Types ===

export type SessionStatus = 
  | 'processing'
  | 'awaiting_approval'
  | 'complete'
  | 'failed';

export interface HumanDecision {
  action: 'approve' | 'revise';
  feedback?: string;
  new_budget?: number;
}
