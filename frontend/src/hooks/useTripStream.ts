import { useCallback, useRef } from 'react';
import { useTrip } from '../context/TripContext';
import type { TripPreferences } from '../types';
import { fetchEventSource } from '@microsoft/fetch-event-source';
import { sessionStorage } from '../utils/sessionStorage';

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
    setStartedAt,
    setPreferences,
    sessionId,
    isStreaming 
  } = useTrip();

  // Ref to track if we have an active connection
  const abortControllerRef = useRef<AbortController | null>(null);
  // Ref to track the current session ID we're listening to (to ignore stale events)
  const activeSessionIdRef = useRef<string | null>(null);

  // Helper to handle incoming SSE messages
  const handleMessage = useCallback((event: any) => {
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
          // Update session storage status
          sessionStorage.update({ status: 'generating' });
          break;

        case 'awaiting_approval':
          setStreamStatus('Ready for review');
          const approvalSessionId = data.session_id;
          if (approvalSessionId) {
            activeSessionIdRef.current = approvalSessionId;
            setSessionId(approvalSessionId);
          }
          setPreview(data.preview);
          setIsStreaming(false);
          // Update session storage status
          sessionStorage.update({ status: 'awaiting_approval' });
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
          // Clear session storage on completion
          sessionStorage.clear();
          break;

        case 'error':
          setStreamError(data.message || 'Unknown error occurred');
          setIsStreaming(false);
          // Clear session storage on error
          sessionStorage.clear();
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
    activeSessionIdRef.current = null; // Reset active session

    // Set started time for tracking
    const now = Date.now();
    setStartedAt(now);
    setPreferences(prefs);
    setIsStreaming(true);
    setStreamError(null);
    setStreamStatus('Initializing agent...');

    // Save initial session to localStorage
    sessionStorage.save({
      sessionId: '', // Will be set when we get the session ID
      preferences: prefs,
      startedAt: now,
      status: 'generating',
      tripTitle: `${prefs.destinations.join(' → ')} Trip`
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
          sessionStorage.clear();
          return;
        } else {
          // Other HTTP errors
          const errorText = await response.text().catch(() => 'Unknown error');
          setStreamError(`Server error (${response.status}): ${errorText}`);
          setIsStreaming(false);
          sessionStorage.clear();
          return;
        }
      }

      // If we get here, response is OK - now open SSE stream
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
      sessionStorage.clear();
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
    // Keep the same active session ID for decision submission
    activeSessionIdRef.current = sessionId;

    setIsStreaming(true);
    setStreamStatus(action === 'approve' ? 'Finalizing trip...' : 'Revising itinerary...');
    setPreview(null);
    
    // Update session storage
    sessionStorage.update({ status: 'finalizing' });

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

  // 3. Reconnect to existing session (for navigation away/back)
  const reconnectSession = async (savedSessionId: string, prefs: TripPreferences, savedStartedAt: number) => {
    // Abort any existing connection
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const controller = new AbortController();
    abortControllerRef.current = controller;
    activeSessionIdRef.current = savedSessionId;

    // Restore state
    setSessionId(savedSessionId);
    setPreferences(prefs);
    setStartedAt(savedStartedAt);
    setIsStreaming(true);
    setStreamError(null);
    setStreamStatus('Reconnecting...');

    try {
      // Check session status first
      const statusRes = await fetch(`/api/trip/session/${savedSessionId}/status`);
      
      if (!statusRes.ok) {
        // Session no longer exists
        setStreamError('Session expired. Please start a new trip.');
        setIsStreaming(false);
        sessionStorage.clear();
        return;
      }

      const status = await statusRes.json();
      console.log('Session status:', status);

      // Handle based on current status
      if (status.status === 'complete') {
        // Trip already completed
        if (status.trip_id) {
          setFinalTripId(status.trip_id);
        }
        setIsStreaming(false);
        sessionStorage.clear();
        return;
      }

      if (status.status === 'awaiting_approval') {
        // Need to show the preview
        setPreview(status.preview);
        setStreamStatus('Ready for review');
        setIsStreaming(false);
        return;
      }

      if (status.status === 'failed') {
        setStreamError(status.error || 'Generation failed');
        setIsStreaming(false);
        sessionStorage.clear();
        return;
      }

      // Still processing - reconnect to stream
      // Note: The backend would need to support a "reconnect" SSE endpoint
      // For now, we'll just poll for status
      setStreamStatus('Resuming generation...');
      
      // Poll for updates
      const pollInterval = setInterval(async () => {
        try {
          const pollRes = await fetch(`/api/trip/session/${savedSessionId}/status`);
          if (!pollRes.ok) {
            clearInterval(pollInterval);
            setStreamError('Session lost');
            setIsStreaming(false);
            sessionStorage.clear();
            return;
          }

          const pollStatus = await pollRes.json();
          
          if (pollStatus.status === 'complete') {
            clearInterval(pollInterval);
            if (pollStatus.trip_id) {
              setFinalTripId(pollStatus.trip_id);
            }
            setIsStreaming(false);
            sessionStorage.clear();
          } else if (pollStatus.status === 'awaiting_approval') {
            clearInterval(pollInterval);
            setPreview(pollStatus.preview);
            setStreamStatus('Ready for review');
            setIsStreaming(false);
          } else if (pollStatus.status === 'failed') {
            clearInterval(pollInterval);
            setStreamError(pollStatus.error || 'Generation failed');
            setIsStreaming(false);
            sessionStorage.clear();
          } else {
            // Still processing
            setStreamStatus(pollStatus.message || 'Processing...');
          }
        } catch (e) {
          console.error('Poll error:', e);
        }
      }, 2000);

      // Clean up on abort
      controller.signal.addEventListener('abort', () => {
        clearInterval(pollInterval);
      });

    } catch (err: any) {
      if (err.name === 'AbortError') return;
      console.error('Failed to reconnect:', err);
      setStreamError('Failed to reconnect. Please start a new trip.');
      setIsStreaming(false);
      sessionStorage.clear();
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
    // Don't clear session storage - the backend is still processing
    // User might want to reconnect
  }, [setIsStreaming]);

  return {
    startGeneration,
    submitDecision,
    reconnectSession,
    cancelStream
  };
};
