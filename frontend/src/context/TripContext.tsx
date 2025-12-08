import { createContext, useContext, useState, type ReactNode } from 'react';
import type { TripPreferences, TripPreview } from '../types';

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

  const resetTrip = () => {
    setPreferences(null);
    setSessionId(null);
    setIsStreaming(false);
    setStreamStatus('');
    setStreamError(null);
    setPreview(null);
    setFinalTripId(null);
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

