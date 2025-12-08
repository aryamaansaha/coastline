import { useState } from 'react';
import { X, Star, RefreshCw, ExternalLink, Search } from 'lucide-react';
import type { DiscoveredPlace, DiscoveryType, Activity } from '../types';
import styles from './DiscoveryDrawer.module.css';

interface DiscoveryDrawerProps {
  activity: Activity;
  tripId: string;
  onClose: () => void;
  // API functions passed from parent
  onDiscover: (activityId: string, type: DiscoveryType, regenerate: boolean) => Promise<DiscoveredPlace[]>;
  onStar: (activityId: string, type: DiscoveryType, placeId: string, starred: boolean) => Promise<void>;
  // Cached discoveries (keyed by type) - source of truth from parent
  discoveries: Partial<Record<DiscoveryType, DiscoveredPlace[]>>;
}

const DISCOVERY_TABS: { type: DiscoveryType; label: string; emoji: string }[] = [
  { type: 'restaurant', label: 'Restaurants', emoji: '🍽️' },
  { type: 'bar', label: 'Bars', emoji: '🍸' },
  { type: 'cafe', label: 'Cafes', emoji: '☕' },
  { type: 'club', label: 'Clubs', emoji: '🎵' },
];

export const DiscoveryDrawer = ({
  activity,
  onClose,
  onDiscover,
  onStar,
  discoveries,
}: DiscoveryDrawerProps) => {
  const [activeType, setActiveType] = useState<DiscoveryType>('restaurant');
  const [loadingType, setLoadingType] = useState<DiscoveryType | null>(null);

  const currentPlaces = discoveries[activeType] || [];
  // A type has been fetched if it exists in discoveries (even if empty array)
  const hasFetched = activeType in discoveries;
  const isLoading = loadingType === activeType;

  const handleFind = async (regenerate = false) => {
    setLoadingType(activeType);
    try {
      await onDiscover(activity.id, activeType, regenerate);
    } finally {
      setLoadingType(null);
    }
  };

  const handleStar = async (placeId: string, starred: boolean) => {
    await onStar(activity.id, activeType, placeId, starred);
  };

  const handleTabChange = (type: DiscoveryType) => {
    setActiveType(type);
  };

  return (
    <div className={styles.drawer}>
      <div className={styles.header}>
        <div>
          <h4 className={styles.title}>Nearby Places</h4>
          <p className={styles.subtitle}>Near {activity.location.name}</p>
        </div>
        <div className={styles.headerActions}>
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
            onClick={() => handleTabChange(tab.type)}
          >
            <span className={styles.tabEmoji}>{tab.emoji}</span>
            {tab.label}
            {/* Show dot indicator if has cached results */}
            {discoveries[tab.type] && discoveries[tab.type]!.length > 0 && (
              <span className={styles.tabDot} />
            )}
          </button>
        ))}
      </div>

      <div className={styles.content}>
        {isLoading ? (
          <div className={styles.loading}>
            <RefreshCw size={24} className={styles.spinning} />
            <p>Finding {activeType}s...</p>
          </div>
        ) : !hasFetched ? (
          // Not yet fetched - show Find button
          <div className={styles.findPrompt}>
            <div className={styles.findIcon}>
              {DISCOVERY_TABS.find(t => t.type === activeType)?.emoji}
            </div>
            <h3>Find {DISCOVERY_TABS.find(t => t.type === activeType)?.label}</h3>
            <p>Discover nearby {activeType}s within walking distance</p>
            <button className={styles.findBtn} onClick={() => handleFind(false)}>
              <Search size={16} /> Find {DISCOVERY_TABS.find(t => t.type === activeType)?.label}
            </button>
          </div>
        ) : currentPlaces.length === 0 ? (
          // Fetched but no results
          <div className={styles.empty}>
            <p>No {activeType}s found nearby.</p>
            <button className={styles.retryBtn} onClick={() => handleFind(true)}>
              <RefreshCw size={14} /> Try Again
            </button>
          </div>
        ) : (
          // Show results
          <>
            <div className={styles.resultsHeader}>
              <span>{currentPlaces.length} {activeType}s found</span>
              <button 
                className={styles.regenerateBtn} 
                onClick={() => handleFind(true)}
                title="Find new places"
              >
                <RefreshCw size={14} /> Refresh
              </button>
            </div>
            {currentPlaces.map(place => (
              <PlaceCard 
                key={place.id} 
                place={place} 
                onStar={(starred) => handleStar(place.id, starred)}
              />
            ))}
          </>
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
