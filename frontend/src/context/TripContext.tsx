import { createContext, useContext, useState, useEffect, type ReactNode } from 'react';
import type { TripPreferences, TripPreview } from '../types';
import { sessionStorage, type ActiveSession } from '../utils/sessionStorage';

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

  // Session persistence
  startedAt: number | null;
  setStartedAt: (time: number | null) => void;
  activeSession: ActiveSession | null;
  hasActiveSession: boolean;
  
  resetTrip: () => void;
  restoreSession: () => ActiveSession | null;
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
  const [startedAt, setStartedAt] = useState<number | null>(null);
  const [activeSession, setActiveSession] = useState<ActiveSession | null>(null);

  // Check for existing session on mount
  useEffect(() => {
    const saved = sessionStorage.get();
    if (saved) {
      console.log('[TripContext] Found saved session:', saved);
      setActiveSession(saved);
    }
  }, []);

  // Update activeSession state whenever relevant state changes
  // Note: sessionId might be empty string initially, so we check preferences && startedAt
  useEffect(() => {
    if (preferences && startedAt) {
      const session: ActiveSession = {
        sessionId: sessionId || '', // Might be empty initially
        preferences,
        startedAt,
        status: preview ? 'awaiting_approval' : (isStreaming ? 'generating' : 'finalizing'),
        tripTitle: `${preferences.destinations.join(' → ')} Trip`
      };
      setActiveSession(session);
      sessionStorage.save(session);
      console.log('[TripContext] Saved session:', session);
    }
  }, [sessionId, preferences, startedAt, isStreaming, preview]);

  // Clear session when trip completes or errors
  useEffect(() => {
    if (finalTripId || streamError) {
      console.log('[TripContext] Clearing session - finalTripId:', finalTripId, 'error:', streamError);
      sessionStorage.clear();
      setActiveSession(null);
    }
  }, [finalTripId, streamError]);

  const resetTrip = () => {
    console.log('[TripContext] Resetting trip');
    setPreferences(null);
    setSessionId(null);
    setIsStreaming(false);
    setStreamStatus('');
    setStreamError(null);
    setPreview(null);
    setFinalTripId(null);
    setStartedAt(null);
    setActiveSession(null);
    sessionStorage.clear();
  };

  const restoreSession = (): ActiveSession | null => {
    const saved = sessionStorage.get();
    if (saved) {
      console.log('[TripContext] Restoring session:', saved);
      setPreferences(saved.preferences);
      setSessionId(saved.sessionId || null);
      setStartedAt(saved.startedAt);
      setActiveSession(saved);
      return saved;
    }
    return null;
  };

  // hasActiveSession is true if we have an active session in localStorage
  // AND we haven't completed or errored yet
  const hasActiveSession = activeSession !== null && !finalTripId && !streamError;

  return (
    <TripContext.Provider value={{
      preferences, setPreferences,
      sessionId, setSessionId,
      isStreaming, setIsStreaming,
      streamStatus, setStreamStatus,
      streamError, setStreamError,
      preview, setPreview,
      finalTripId, setFinalTripId,
      startedAt, setStartedAt,
      activeSession,
      hasActiveSession,
      resetTrip,
      restoreSession
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
