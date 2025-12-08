import { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { RefreshCw } from 'lucide-react';
import { useTrip } from '../context/TripContext';
import { useTripStream } from '../hooks/useTripStream';
import styles from './LoadingPage.module.css';

export const LoadingPage = () => {
  const navigate = useNavigate();
  const { 
    streamStatus, 
    resetTrip, 
    sessionId, 
    activeSession,
    setPreview,
    setFinalTripId,
    setStreamError,
    clearActiveSession,
    setIsStreaming,
    setStreamStatus
  } = useTrip();
  const { cancelStream } = useTripStream();
  const pollingRef = useRef<number | null>(null);

  // Poll for status updates when we have an active session but might not have SSE
  // This handles the case where user navigated away and came back
  useEffect(() => {
    // Only poll if we have a session ID and it's not 'pending'
    const effectiveSessionId = sessionId || (activeSession?.sessionId !== 'pending' ? activeSession?.sessionId : null);
    
    if (!effectiveSessionId) return;

    const pollStatus = async () => {
      try {
        const res = await fetch(`/api/trip/session/${effectiveSessionId}/status`);
        if (!res.ok) {
          if (res.status === 404) {
            // Session expired
            setStreamError('Session expired. Please start a new trip.');
            clearActiveSession();
            setIsStreaming(false);
            return;
          }
          throw new Error('Failed to fetch status');
        }

        const status = await res.json();
        
        // Update status message
        if (status.status === 'processing') {
          setStreamStatus('Trip generation in progress...');
        }

        // Check for completion or review
        if (status.status === 'awaiting_approval' && status.preview) {
          setPreview(status.preview);
          setIsStreaming(false);
          if (pollingRef.current) clearInterval(pollingRef.current);
        } else if (status.status === 'complete' && status.final_itinerary) {
          setFinalTripId(status.final_itinerary.trip_id);
          clearActiveSession();
          if (pollingRef.current) clearInterval(pollingRef.current);
        } else if (status.status === 'failed') {
          setStreamError(status.error_message || 'Trip generation failed');
          clearActiveSession();
          setIsStreaming(false);
          if (pollingRef.current) clearInterval(pollingRef.current);
        }
      } catch (err) {
        console.error('Status poll failed:', err);
      }
    };

    // Poll every 3 seconds
    pollingRef.current = window.setInterval(pollStatus, 3000);
    // Also poll immediately
    pollStatus();

    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
      }
    };
  }, [sessionId, activeSession, setPreview, setFinalTripId, setStreamError, clearActiveSession, setIsStreaming, setStreamStatus]);

  const handleCancel = async () => {
    // Stop polling
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
    }
    
    // Abort any active SSE connection
    cancelStream();
    
    // Delete backend session if it exists
    const effectiveSessionId = sessionId || activeSession?.sessionId;
    if (effectiveSessionId && effectiveSessionId !== 'pending') {
      try {
        await fetch(`/api/trip/session/${effectiveSessionId}`, { method: 'DELETE' });
      } catch (err) {
        console.error('Failed to delete session:', err);
      }
    }
    
    // Clear active session from localStorage
    clearActiveSession();
    
    // Clear frontend state and navigate away
    resetTrip();
    navigate('/');
  };

  return (
    <div className={styles.container}>
      <RefreshCw size={40} className={styles.spinner} />
      <h2 className={styles.title}>Designing your trip...</h2>
      
      <div className={styles.terminal}>
        <div className={styles.terminalHeader}>
          <span className={styles.dot} />
          <span className={styles.dot} />
          <span className={styles.dot} />
        </div>
        <div className={styles.terminalBody}>
          <div className={styles.line}>
            <span className={styles.prompt}>{'>'}</span>
            {streamStatus || 'Initializing agent...'}
          </div>
        </div>
      </div>

      <p className={styles.hint}>This usually takes 30-60 seconds</p>
      <p className={styles.navHint}>
        Feel free to navigate away. Your trip will keep generating in the background.
      </p>
      
      <button className={styles.cancelBtn} onClick={handleCancel}>
        Cancel
      </button>
    </div>
  );
};
