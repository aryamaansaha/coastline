import { useState, useCallback } from 'react';
import type { Itinerary, DiscoveredPlace, DiscoveryType } from '../types';

const API_BASE = '/api';
const TOKEN_KEY = 'coastline_token';

// Helper to get auth headers
const getAuthHeaders = (): HeadersInit => {
  const token = localStorage.getItem(TOKEN_KEY);
  const headers: HeadersInit = {
    'Content-Type': 'application/json'
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
};

// --- Trip API ---
export const useTrips = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const getTrip = useCallback(async (tripId: string): Promise<Itinerary | null> => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/trip/${tripId}`, {
        headers: getAuthHeaders()
      });
      if (!res.ok) throw new Error('Trip not found');
      return await res.json();
    } catch (err: any) {
      setError(err.message);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const listTrips = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/trips`, {
        headers: getAuthHeaders()
      });
      if (!res.ok) throw new Error('Failed to fetch trips');
      return await res.json();
    } catch (err: any) {
      setError(err.message);
      return [];
    } finally {
      setLoading(false);
    }
  }, []);

  const deleteTrip = useCallback(async (tripId: string): Promise<boolean> => {
    try {
      const res = await fetch(`${API_BASE}/trip/${tripId}`, {
        method: 'DELETE',
        headers: getAuthHeaders()
      });
      return res.ok;
    } catch {
      return false;
    }
  }, []);

  const claimTrip = useCallback(async (tripId: string): Promise<boolean> => {
    try {
      const res = await fetch(`${API_BASE}/trip/${tripId}/claim`, {
        method: 'POST',
        headers: getAuthHeaders()
      });
      return res.ok;
    } catch {
      return false;
    }
  }, []);

  return { getTrip, listTrips, deleteTrip, claimTrip, loading, error };
};

// --- Discovery API ---
export const useDiscovery = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const discoverPlaces = useCallback(async (
    tripId: string,
    activityId: string,
    placeType: DiscoveryType,
    regenerate = false
  ): Promise<DiscoveredPlace[]> => {
    setLoading(true);
    setError(null);
    try {
      const url = `${API_BASE}/trip/${tripId}/activities/${activityId}/discover/${placeType}?regenerate=${regenerate}`;
      const res = await fetch(url, {
        method: 'POST',
        headers: getAuthHeaders()
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Discovery failed');
      }

      return await res.json();
    } catch (err: any) {
      setError(err.message);
      return [];
    } finally {
      setLoading(false);
    }
  }, []);

  const starPlace = useCallback(async (
    tripId: string,
    activityId: string,
    placeType: DiscoveryType,
    placeId: string,
    starred: boolean
  ): Promise<DiscoveredPlace | null> => {
    try {
      const url = `${API_BASE}/trip/${tripId}/activities/${activityId}/discover/${placeType}/${placeId}/star`;
      const res = await fetch(url, {
        method: 'PUT',
        headers: getAuthHeaders(),
        body: JSON.stringify({ starred })
      });

      if (!res.ok) return null;
      return await res.json();
    } catch {
      return null;
    }
  }, []);

  const getAllDiscoveries = useCallback(async (tripId: string) => {
    try {
      const res = await fetch(`${API_BASE}/trip/${tripId}/discoveries`, {
        headers: getAuthHeaders()
      });
      if (!res.ok) return [];
      return await res.json();
    } catch {
      return [];
    }
  }, []);

  return { discoverPlaces, starPlace, getAllDiscoveries, loading, error };
};

// --- Trip Summary type for listing ---
export interface TripSummary {
  trip_id: string;
  trip_title: string;
  budget_limit: number;
  destinations: string[];
  num_days: number;
  created_at: string | null;
  updated_at: string | null;
}

