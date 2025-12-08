import { useNavigate } from 'react-router-dom';
import { RefreshCw } from 'lucide-react';
import { useTrip } from '../context/TripContext';
import { useTripStream } from '../hooks/useTripStream';
import styles from './LoadingPage.module.css';

export const LoadingPage = () => {
  const navigate = useNavigate();
  const { streamStatus, resetTrip, sessionId } = useTrip();
  const { cancelStream } = useTripStream();

  const handleCancel = async () => {
    // Abort any active SSE connection
    cancelStream();
    
    // Delete backend session if it exists
    if (sessionId) {
      try {
        await fetch(`/api/trip/session/${sessionId}`, { method: 'DELETE' });
      } catch (err) {
        console.error('Failed to delete session:', err);
      }
    }
    
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
      
      <button className={styles.cancelBtn} onClick={handleCancel}>
        Cancel
      </button>
    </div>
  );
};
