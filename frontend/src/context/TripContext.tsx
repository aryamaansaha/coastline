import { createContext, useContext, useState, useEffect, type ReactNode } from 'react';
import type { TripPreferences, TripPreview } from '../types';

const ACTIVE_SESSION_KEY = 'coastline_active_session';

// Data persisted to localStorage for in-progress trips
export interface ActiveSession {
  sessionId: string;
  preferences: TripPreferences;
  startedAt: number; // timestamp
  tripTitle?: string; // Set once we get first preview
}

interface TripContextType {
  preferences: TripPreferences | null;
  setPreferences: (prefs: TripPreferences) => void;
  
  sessionId: string | null;
  setSessionId: (id: string | null) => void;
  
  // SSE State
  isStreaming: boolean;
  setIsStreaming: (streaming: boolean) => void;
  streamStatus: string;
  setStreamStatus: (status: string) => void;
  streamError: string | null;
  setStreamError: (err: string | null) => void;
  
  // HITL State
  preview: TripPreview | null;
  setPreview: (preview: TripPreview | null) => void;
  
  // Final Result
  finalTripId: string | null;
  setFinalTripId: (id: string | null) => void;

  // Active Session Persistence
  activeSession: ActiveSession | null;
  saveActiveSession: (session: ActiveSession) => void;
  clearActiveSession: () => void;

  resetTrip: () => void;
}

const TripContext = createContext<TripContextType | undefined>(undefined);

export const TripProvider = ({ children }: { children: ReactNode }) => {
  const [preferences, setPreferences] = useState<TripPreferences | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [streamStatus, setStreamStatus] = useState<string>('');
  const [streamError, setStreamError] = useState<string | null>(null);
  const [preview, setPreview] = useState<TripPreview | null>(null);
  const [finalTripId, setFinalTripId] = useState<string | null>(null);
  const [activeSession, setActiveSession] = useState<ActiveSession | null>(null);

  // Load active session from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(ACTIVE_SESSION_KEY);
      if (stored) {
        const session = JSON.parse(stored) as ActiveSession;
        // Only restore if less than 24 hours old
        const age = Date.now() - session.startedAt;
        if (age < 24 * 60 * 60 * 1000) {
          setActiveSession(session);
        } else {
          localStorage.removeItem(ACTIVE_SESSION_KEY);
        }
      }
    } catch (e) {
      console.error('Failed to load active session:', e);
      localStorage.removeItem(ACTIVE_SESSION_KEY);
    }
  }, []);

  const saveActiveSession = (session: ActiveSession) => {
    setActiveSession(session);
    localStorage.setItem(ACTIVE_SESSION_KEY, JSON.stringify(session));
  };

  const clearActiveSession = () => {
    setActiveSession(null);
    localStorage.removeItem(ACTIVE_SESSION_KEY);
  };

  const resetTrip = () => {
    setPreferences(null);
    setSessionId(null);
    setIsStreaming(false);
    setStreamStatus('');
    setStreamError(null);
    setPreview(null);
    setFinalTripId(null);
    // Note: Don't clear activeSession here - that's managed separately
  };

  return (
    <TripContext.Provider value={{
      preferences, setPreferences,
      sessionId, setSessionId,
      isStreaming, setIsStreaming,
      streamStatus, setStreamStatus,
      streamError, setStreamError,
      preview, setPreview,
      finalTripId, setFinalTripId,
      activeSession, saveActiveSession, clearActiveSession,
      resetTrip
    }}>
      {children}
    </TripContext.Provider>
  );
};

export const useTrip = () => {
  const context = useContext(TripContext);
  if (context === undefined) {
    throw new Error('useTrip must be used within a TripProvider');
  }
  return context;
};
