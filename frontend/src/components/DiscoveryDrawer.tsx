import { X, Star, RefreshCw, ExternalLink } from 'lucide-react';
import type { DiscoveredPlace, DiscoveryType, Activity } from '../types';
import styles from './DiscoveryDrawer.module.css';

interface DiscoveryDrawerProps {
  activity: Activity;
  places: DiscoveredPlace[];
  isLoading: boolean;
  activeType: DiscoveryType;
  onTypeChange: (type: DiscoveryType) => void;
  onStar: (placeId: string, starred: boolean) => void;
  onRegenerate: () => void;
  onClose: () => void;
}

const DISCOVERY_TABS: { type: DiscoveryType; label: string; emoji: string }[] = [
  { type: 'restaurant', label: 'Restaurants', emoji: '🍽️' },
  { type: 'bar', label: 'Bars', emoji: '🍸' },
  { type: 'cafe', label: 'Cafes', emoji: '☕' },
  { type: 'club', label: 'Clubs', emoji: '🎵' },
];

export const DiscoveryDrawer = ({
  activity,
  places,
  isLoading,
  activeType,
  onTypeChange,
  onStar,
  onRegenerate,
  onClose,
}: DiscoveryDrawerProps) => {
  return (
    <div className={styles.drawer}>
      <div className={styles.header}>
        <div>
          <h4 className={styles.title}>Nearby Places</h4>
          <p className={styles.subtitle}>Near {activity.location.name}</p>
        </div>
        <div className={styles.headerActions}>
          <button 
            className={styles.refreshBtn} 
            onClick={onRegenerate}
            disabled={isLoading}
            title="Find new places"
          >
            <RefreshCw size={16} className={isLoading ? styles.spinning : ''} />
          </button>
          <button className={styles.closeBtn} onClick={onClose}>
            <X size={18} />
          </button>
        </div>
      </div>

      <div className={styles.tabs}>
        {DISCOVERY_TABS.map(tab => (
          <button
            key={tab.type}
            className={`${styles.tab} ${activeType === tab.type ? styles.active : ''}`}
            onClick={() => onTypeChange(tab.type)}
          >
            <span className={styles.tabEmoji}>{tab.emoji}</span>
            {tab.label}
          </button>
        ))}
      </div>

      <div className={styles.content}>
        {isLoading ? (
          <div className={styles.loading}>
            <RefreshCw size={24} className={styles.spinning} />
            <p>Finding places...</p>
          </div>
        ) : places.length === 0 ? (
          <div className={styles.empty}>
            <p>No {activeType}s found nearby.</p>
            <button className={styles.retryBtn} onClick={onRegenerate}>
              Try Again
            </button>
          </div>
        ) : (
          places.map(place => (
            <PlaceCard 
              key={place.id} 
              place={place} 
              onStar={(starred) => onStar(place.id, starred)}
            />
          ))
        )}
      </div>
    </div>
  );
};

// --- Place Card Sub-component ---
const PlaceCard = ({ 
  place, 
  onStar 
}: { 
  place: DiscoveredPlace; 
  onStar: (starred: boolean) => void;
}) => {
  return (
    <div className={styles.placeCard}>
      <div className={styles.placeTop}>
        <span className={styles.placeName}>{place.name}</span>
        <button 
          className={`${styles.starBtn} ${place.starred ? styles.starred : ''}`}
          onClick={() => onStar(!place.starred)}
        >
          <Star size={16} fill={place.starred ? 'currentColor' : 'none'} />
        </button>
      </div>
      
      <div className={styles.placeMeta}>
        {place.rating && (
          <>
            <span className={styles.rating}>
              <Star size={12} fill="currentColor" /> {place.rating.toFixed(1)}
            </span>
            <span>•</span>
          </>
        )}
        {place.price_range && (
          <>
            <span>{place.price_range}</span>
            <span>•</span>
          </>
        )}
        <span className={styles.type}>{place.place_type}</span>
      </div>
      
      <div className={styles.placeAddress}>{place.address}</div>
      
      {place.google_maps_url && (
        <a 
          href={place.google_maps_url} 
          target="_blank" 
          rel="noopener noreferrer"
          className={styles.mapsLink}
        >
          <ExternalLink size={12} /> Open in Maps
        </a>
      )}
    </div>
  );
};

