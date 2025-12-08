import type { Day, Activity } from '../types';
import { ActivityCard } from './ActivityCard';
import styles from './DaySection.module.css';

interface DaySectionProps {
  day: Day;
  highlightedActivityId?: string | null;
  showDiscovery?: boolean;
  onDiscoveryClick?: (activity: Activity) => void;
  onActivityClick?: (activity: Activity) => void;
}

export const DaySection = ({ 
  day, 
  highlightedActivityId,
  showDiscovery = false,
  onDiscoveryClick,
  onActivityClick 
}: DaySectionProps) => {
  return (
    <div className={styles.section}>
      <div className={styles.header}>
        <h3 className={styles.title}>Day {day.day_number}: {day.city}</h3>
        <span className={styles.theme}>{day.theme}</span>
      </div>
      
      <div className={styles.activities}>
        {day.activities.map((activity, index) => (
          <ActivityCard
            key={activity.id || `activity-${day.day_number}-${index}`}
            activity={activity}
            isHighlighted={highlightedActivityId === activity.id}
            showDiscovery={showDiscovery}
            onDiscoveryClick={() => onDiscoveryClick?.(activity)}
            onCardClick={() => onActivityClick?.(activity)}
          />
        ))}
      </div>
    </div>
  );
};

