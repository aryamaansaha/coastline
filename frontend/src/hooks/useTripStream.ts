import { useCallback, useRef } from 'react';
import { useTrip } from '../context/TripContext';
import type { TripPreferences } from '../types';
import { fetchEventSource } from '@microsoft/fetch-event-source';

// Custom error to signal we should stop retrying
class FatalError extends Error {}

export const useTripStream = () => {
  const { 
    setSessionId, 
    setStreamStatus, 
    setPreview, 
    setFinalTripId,
    setIsStreaming,
    setStreamError,
    sessionId,
    isStreaming 
  } = useTrip();

  // Ref to track if we have an active connection
  const abortControllerRef = useRef<AbortController | null>(null);

  // Helper to handle incoming SSE messages
  const handleMessage = useCallback((event: any) => {
    try {
      // SSE events have: event.type (the event name) and event.data (JSON string)
      const eventType = event.event || 'message';
      const data = event.data ? JSON.parse(event.data) : {};
      
      console.log('SSE Event:', eventType, data);

      switch (eventType) {
        case 'starting':
        case 'searching':
        case 'planning':
        case 'validating':
          setStreamStatus(data.message || 'Processing...');
          break;

        case 'awaiting_approval':
          setStreamStatus('Ready for review');
          setSessionId(data.session_id);
          setPreview(data.preview);
          setIsStreaming(false);
          break;

        case 'complete':
          setStreamStatus('Trip generated!');
          // Try to get trip_id from multiple possible locations
          const tripId = data.trip_id || data.itinerary?.trip_id;
          console.log('✅ Trip complete! trip_id:', tripId, 'Full data:', data);
          if (tripId) {
            setFinalTripId(tripId);
          } else {
            console.error('⚠️ Complete event missing trip_id:', data);
          }
          setIsStreaming(false);
          break;

        case 'error':
          setStreamError(data.message || 'Unknown error occurred');
          setIsStreaming(false);
          break;
          
        default:
          console.log('Unknown SSE event type:', eventType);
      }
    } catch (err) {
      console.error('Error parsing SSE message:', err, 'Raw:', event);
    }
  }, [setSessionId, setStreamStatus, setPreview, setFinalTripId, setIsStreaming, setStreamError]);

  // 1. Start Generation (Initial POST)
  const startGeneration = async (prefs: TripPreferences) => {
    // Prevent duplicate requests
    if (isStreaming) {
      console.log('Already streaming, ignoring duplicate request');
      return;
    }

    // Abort any existing connection
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const controller = new AbortController();
    abortControllerRef.current = controller;

    setIsStreaming(true);
    setStreamError(null);
    setStreamStatus('Initializing agent...');

    try {
      await fetchEventSource('/api/trip/generate/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(prefs),
        signal: controller.signal,
        onmessage: handleMessage,
        onclose: () => {
          console.log('SSE connection closed normally');
        },
        onerror: (err) => {
          console.error('SSE Error:', err);
          // Don't retry - throw fatal error to stop
          throw new FatalError('Connection failed');
        },
        // Disable automatic retry
        openWhenHidden: true,
      });
    } catch (err: any) {
      if (err.name === 'AbortError') {
        console.log('SSE connection aborted');
        return;
      }
      console.error('Failed to start generation:', err);
      setStreamError('Failed to connect. Please try again.');
      setIsStreaming(false);
    }
  };

  // 2. Submit Decision (Resume Stream)
  const submitDecision = async (action: 'approve' | 'revise', feedback?: string, newBudget?: number) => {
    if (!sessionId) return;

    // Abort any existing connection
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const controller = new AbortController();
    abortControllerRef.current = controller;

    setIsStreaming(true);
    setStreamStatus(action === 'approve' ? 'Finalizing trip...' : 'Revising itinerary...');
    setPreview(null);

    try {
      await fetchEventSource(`/api/trip/session/${sessionId}/decide`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, feedback, new_budget: newBudget }),
        signal: controller.signal,
        onmessage: handleMessage,
        onerror: (err) => {
          console.error('SSE Resume Error:', err);
          throw new FatalError('Decision submission failed');
        },
        openWhenHidden: true,
      });
    } catch (err: any) {
      if (err.name === 'AbortError') return;
      setStreamError('Failed to submit decision');
      setIsStreaming(false);
    }
  };

  return {
    startGeneration,
    submitDecision
  };
};
