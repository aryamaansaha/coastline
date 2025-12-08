import { RefreshCw } from 'lucide-react';
import { useTrip } from '../context/TripContext';
import styles from './LoadingPage.module.css';

export const LoadingPage = () => {
  const { streamStatus, resetTrip } = useTrip();

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
      
      <button className={styles.cancelBtn} onClick={resetTrip}>
        Cancel
      </button>
    </div>
  );
};
