import { Plane, Hotel, MapPin, Search } from 'lucide-react';
import type { Activity } from '../types';
import styles from './ActivityCard.module.css';

interface ActivityCardProps {
  activity: Activity;
  isHighlighted?: boolean;
  showDiscovery?: boolean;
  onDiscoveryClick?: () => void;
  onCardClick?: () => void;
}

export const ActivityCard = ({ 
  activity, 
  isHighlighted = false,
  showDiscovery = false,
  onDiscoveryClick,
  onCardClick 
}: ActivityCardProps) => {
  
  const getIcon = () => {
    switch (activity.type) {
      case 'flight': return <Plane size={16} color="#3b82f6" />;
      case 'hotel': return <Hotel size={16} color="#8b5cf6" />;
      default: return <MapPin size={16} color="#10b981" />;
    }
  };

  return (
    <div 
      className={`${styles.card} ${isHighlighted ? styles.highlighted : ''}`}
      onClick={onCardClick}
    >
      <div className={styles.timeCol}>{activity.time_slot}</div>
      <div className={styles.infoCol}>
        <div className={styles.title}>
          {getIcon()} {activity.title}
        </div>
        <div className={styles.desc}>{activity.description}</div>
        
        {activity.activity_suggestion && (
          <div className={styles.suggestion}>💡 {activity.activity_suggestion}</div>
        )}
        
        <div className={styles.footer}>
          <div className={styles.costArea}>
            {activity.estimated_cost > 0 && (
              <span className={styles.cost}>${activity.estimated_cost.toFixed(0)}</span>
            )}
            {activity.price_suggestion && (
              <span className={styles.priceTip} title={activity.price_suggestion}>ℹ️</span>
            )}
          </div>
          
          {showDiscovery && activity.type === 'activity' && (
            <button 
              className={styles.discoveryBtn}
              onClick={(e) => {
                e.stopPropagation();
                onDiscoveryClick?.();
              }}
            >
              <Search size={12} /> Find Nearby
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

