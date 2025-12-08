import { useCallback, useRef } from 'react';
import { useTrip, type ActiveSession } from '../context/TripContext';
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
    setPreferences,
    sessionId,
    isStreaming,
    saveActiveSession,
    clearActiveSession,
  } = useTrip();

  // Ref to track if we have an active connection
  const abortControllerRef = useRef<AbortController | null>(null);
  // Ref to track the current session ID we're listening to (to ignore stale events)
  const activeSessionIdRef = useRef<string | null>(null);

  // Helper to handle incoming SSE messages
  const handleMessage = useCallback((event: any, prefs?: TripPreferences) => {
    try {
      // SSE events have: event.type (the event name) and event.data (JSON string)
      const eventType = event.event || 'message';
      const data = event.data ? JSON.parse(event.data) : {};
      
      // Ignore events if they're for a different session (cancelled session)
      const eventSessionId = data.session_id;
      if (eventSessionId && activeSessionIdRef.current && eventSessionId !== activeSessionIdRef.current) {
        console.log('Ignoring SSE event for cancelled session:', eventSessionId);
        return;
      }
      
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
          const approvalSessionId = data.session_id;
          if (approvalSessionId) {
            activeSessionIdRef.current = approvalSessionId;
            setSessionId(approvalSessionId);
            
            // Update active session with title from preview
            if (prefs && data.preview?.itinerary?.trip_title) {
              saveActiveSession({
                sessionId: approvalSessionId,
                preferences: prefs,
                startedAt: Date.now(),
                tripTitle: data.preview.itinerary.trip_title
              });
            }
          }
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
          // Clear active session on completion
          clearActiveSession();
          break;

        case 'error':
          setStreamError(data.message || 'Unknown error occurred');
          setIsStreaming(false);
          // Clear active session on error
          clearActiveSession();
          break;
          
        default:
          console.log('Unknown SSE event type:', eventType);
      }
    } catch (err) {
      console.error('Error parsing SSE message:', err, 'Raw:', event);
    }
  }, [setSessionId, setStreamStatus, setPreview, setFinalTripId, setIsStreaming, setStreamError, saveActiveSession, clearActiveSession]);

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
    activeSessionIdRef.current = null; // Reset active session

    setIsStreaming(true);
    setStreamError(null);
    setStreamStatus('Initializing agent...');

    // Save active session immediately (without session ID yet)
    saveActiveSession({
      sessionId: 'pending', // Will be updated when we get the real session ID
      preferences: prefs,
      startedAt: Date.now(),
      tripTitle: `Trip to ${prefs.destinations.join(', ')}`
    });

    try {
      // First, check if the request will succeed (handle validation errors)
      const response = await fetch('/api/trip/generate/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(prefs),
        signal: controller.signal,
      });

      // Handle validation errors (422) before opening SSE stream
      if (!response.ok) {
        if (response.status === 422) {
          // Validation error - parse and display details
          const errorData = await response.json().catch(() => ({}));
          const detail = errorData.detail || [];
          let errorMessage = 'Validation error: ';
          
          if (Array.isArray(detail)) {
            const errors = detail.map((err: any) => {
              const field = err.loc?.join('.') || 'unknown';
              const msg = err.msg || 'Invalid value';
              return `${field}: ${msg}`;
            }).join(', ');
            errorMessage += errors;
          } else if (typeof detail === 'string') {
            errorMessage += detail;
          } else {
            errorMessage += 'Please check your input values';
          }
          
          setStreamError(errorMessage);
          setIsStreaming(false);
          clearActiveSession();
          return;
        } else {
          // Other HTTP errors
          const errorText = await response.text().catch(() => 'Unknown error');
          setStreamError(`Server error (${response.status}): ${errorText}`);
          setIsStreaming(false);
          clearActiveSession();
          return;
        }
      }

      // If we get here, response is OK - now open SSE stream
      await fetchEventSource('/api/trip/generate/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(prefs),
        signal: controller.signal,
        onmessage: (event) => handleMessage(event, prefs),
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
      clearActiveSession();
    }
  };

  // 2. Reconnect to existing session
  const reconnectToSession = async (session: ActiveSession): Promise<'streaming' | 'review' | 'complete' | 'error' | 'not_found'> => {
    try {
      // First, get the current session status
      const res = await fetch(`/api/trip/session/${session.sessionId}/status`);
      
      if (!res.ok) {
        if (res.status === 404) {
          clearActiveSession();
          return 'not_found';
        }
        throw new Error('Failed to get session status');
      }

      const status = await res.json();
      console.log('Session status:', status);

      // Restore preferences
      setPreferences(session.preferences);

      switch (status.status) {
        case 'processing':
          // Still processing - set up streaming state
          setIsStreaming(true);
          setStreamStatus('Trip generation in progress...');
          setSessionId(session.sessionId);
          activeSessionIdRef.current = session.sessionId;
          return 'streaming';

        case 'awaiting_approval':
          // Ready for review
          setSessionId(session.sessionId);
          activeSessionIdRef.current = session.sessionId;
          setPreview(status.preview);
          setIsStreaming(false);
          setStreamStatus('Ready for review');
          return 'review';

        case 'complete':
          // Already completed
          if (status.final_itinerary?.trip_id) {
            setFinalTripId(status.final_itinerary.trip_id);
          }
          clearActiveSession();
          return 'complete';

        case 'failed':
          setStreamError(status.error_message || 'Trip generation failed');
          clearActiveSession();
          return 'error';

        default:
          console.warn('Unknown session status:', status.status);
          return 'error';
      }
    } catch (err) {
      console.error('Failed to reconnect to session:', err);
      clearActiveSession();
      return 'error';
    }
  };

  // 3. Submit Decision (Resume Stream)
  const submitDecision = async (action: 'approve' | 'revise', feedback?: string, newBudget?: number) => {
    if (!sessionId) return;

    // Abort any existing connection
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const controller = new AbortController();
    abortControllerRef.current = controller;
    // Keep the same active session ID for decision submission
    activeSessionIdRef.current = sessionId;

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

  // 4. Cancel/Abort Stream
  const cancelStream = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    activeSessionIdRef.current = null; // Clear active session
    setIsStreaming(false);
    clearActiveSession();
  }, [setIsStreaming, clearActiveSession]);

  return {
    startGeneration,
    reconnectToSession,
    submitDecision,
    cancelStream
  };
};
