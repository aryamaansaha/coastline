import { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { RefreshCw, ArrowLeft } from 'lucide-react';
import { useTrip } from '../context/TripContext';
import { useTripStream } from '../hooks/useTripStream';
import { sessionStorage } from '../utils/sessionStorage';
import styles from './LoadingPage.module.css';

export const LoadingPage = () => {
  const navigate = useNavigate();
  const { 
    streamStatus, 
    resetTrip, 
    sessionId, 
    activeSession, 
    startedAt,
    isStreaming 
  } = useTrip();
  const { cancelStream, reconnectSession } = useTripStream();
  const [elapsedTime, setElapsedTime] = useState('');
  const hasAttemptedReconnect = useRef(false);

  // Attempt to reconnect if we have a saved session but not streaming
  useEffect(() => {
    if (!hasAttemptedReconnect.current && activeSession && !isStreaming) {
      hasAttemptedReconnect.current = true;
      console.log('Attempting to reconnect to session:', activeSession.sessionId);
      
      if (activeSession.sessionId) {
        reconnectSession(
          activeSession.sessionId, 
          activeSession.preferences, 
          activeSession.startedAt
        );
      }
    }
  }, [activeSession, isStreaming, reconnectSession]);

  // Update elapsed time
  useEffect(() => {
    const effectiveStartedAt = startedAt || activeSession?.startedAt;
    if (!effectiveStartedAt) return;
    
    const update = () => {
      setElapsedTime(sessionStorage.getElapsedTime(effectiveStartedAt));
    };
    
    update();
    const interval = setInterval(update, 1000);
    return () => clearInterval(interval);
  }, [startedAt, activeSession?.startedAt]);

  const handleCancel = async () => {
    // Abort any active SSE connection
    cancelStream();
    
    // Delete backend session if it exists
    const effectiveSessionId = sessionId || activeSession?.sessionId;
    if (effectiveSessionId) {
      try {
        await fetch(`/api/trip/session/${effectiveSessionId}`, { method: 'DELETE' });
      } catch (err) {
        console.error('Failed to delete session:', err);
      }
    }
    
    // Clear frontend state and navigate away
    sessionStorage.clear();
    resetTrip();
    navigate('/');
  };

  const handleBackToTrips = () => {
    // Don't cancel - just navigate away
    // The session continues in the background
    navigate('/');
  };

  return (
    <div className={styles.container}>
      <button className={styles.backBtn} onClick={handleBackToTrips}>
        <ArrowLeft size={18} /> Back to My Trips
      </button>

      <div className={styles.content}>
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

        <div className={styles.meta}>
          {elapsedTime && <span className={styles.elapsed}>{elapsedTime} elapsed</span>}
          <span className={styles.hint}>This usually takes a couple of minutes</span>
        </div>
        
        <div className={styles.actions}>
          <button className={styles.cancelBtn} onClick={handleCancel}>
            Cancel Generation
          </button>
        </div>

        <p className={styles.navHint}>
          💡 You can navigate away - your trip will continue generating in the background
        </p>
      </div>
    </div>
  );
};
