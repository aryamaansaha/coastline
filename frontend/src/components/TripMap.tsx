import { useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import type { Activity } from '../types';
import 'leaflet/dist/leaflet.css';
import styles from './TripMap.module.css';

// Common city coordinates for fallback centering
const CITY_COORDS: Record<string, [number, number]> = {
  'london': [51.5074, -0.1278],
  'paris': [48.8566, 2.3522],
  'new york': [40.7128, -74.0060],
  'los angeles': [34.0522, -118.2437],
  'tokyo': [35.6762, 139.6503],
  'rome': [41.9028, 12.4964],
  'barcelona': [41.3851, 2.1734],
  'amsterdam': [52.3676, 4.9041],
  'berlin': [52.5200, 13.4050],
  'madrid': [40.4168, -3.7038],
  'seattle': [47.6062, -122.3321],
  'san francisco': [37.7749, -122.4194],
  'chicago': [41.8781, -87.6298],
  'miami': [25.7617, -80.1918],
  'sydney': [-33.8688, 151.2093],
  'dubai': [25.2048, 55.2708],
  'singapore': [1.3521, 103.8198],
  'hong kong': [22.3193, 114.1694],
  'lisbon': [38.7223, -9.1393],
  'prague': [50.0755, 14.4378],
  'vienna': [48.2082, 16.3738],
  'munich': [48.1351, 11.5820],
  'florence': [43.7696, 11.2558],
  'venice': [45.4408, 12.3155],
  'milan': [45.4642, 9.1900],
};

// Default center (Europe)
const DEFAULT_CENTER: [number, number] = [48.8566, 2.3522];

interface TripMapProps {
  activities: Activity[];
  selectedActivity?: Activity | null;
  onActivitySelect?: (activity: Activity) => void;
  // For preview mode (no coordinates yet)
  fallbackCities?: string[];
}

// Component to auto-fit bounds
function FitBounds({ activities }: { activities: Activity[] }) {
  const map = useMap();
  
  useEffect(() => {
    const validActivities = activities.filter(a => a.location.lat && a.location.lng);
    if (validActivities.length === 0) return;
    
    const coords = validActivities.map(a => [a.location.lat!, a.location.lng!] as [number, number]);
    if (coords.length === 1) {
      map.setView(coords[0], 13);
    } else {
      const lats = coords.map(c => c[0]);
      const lngs = coords.map(c => c[1]);
      const bounds: [[number, number], [number, number]] = [
        [Math.min(...lats), Math.min(...lngs)],
        [Math.max(...lats), Math.max(...lngs)]
      ];
      map.fitBounds(bounds, { padding: [50, 50] });
    }
  }, [activities, map]);
  
  return null;
}

// Component to fly to selected activity
function FlyToSelected({ activity }: { activity: Activity | null | undefined }) {
  const map = useMap();
  
  useEffect(() => {
    if (activity?.location.lat && activity?.location.lng) {
      map.flyTo([activity.location.lat, activity.location.lng], 14, { duration: 0.5 });
    }
  }, [activity, map]);
  
  return null;
}

// Helper component to set initial view
function SetViewOnMount({ center, zoom }: { center: [number, number]; zoom: number }) {
  const map = useMap();
  
  useEffect(() => {
    map.setView(center, zoom);
  }, []);
  
  return null;
}

// Get center from city names
function getCenterFromCities(cities: string[]): [number, number] {
  for (const city of cities) {
    const normalized = city.toLowerCase().trim();
    if (CITY_COORDS[normalized]) {
      return CITY_COORDS[normalized];
    }
    // Try partial match
    for (const [key, coords] of Object.entries(CITY_COORDS)) {
      if (normalized.includes(key) || key.includes(normalized)) {
        return coords;
      }
    }
  }
  return DEFAULT_CENTER;
}

export const TripMap = ({ 
  activities, 
  selectedActivity, 
  onActivitySelect,
  fallbackCities = []
}: TripMapProps) => {
  const validActivities = activities.filter(a => a.location.lat && a.location.lng);
  const hasValidActivities = validActivities.length > 0;
  
  // Determine center
  let center: [number, number];
  let zoom: number;
  
  if (hasValidActivities) {
    center = [validActivities[0].location.lat!, validActivities[0].location.lng!];
    zoom = 12;
  } else if (fallbackCities.length > 0) {
    center = getCenterFromCities(fallbackCities);
    zoom = 10; // Zoomed out for preview
  } else {
    center = DEFAULT_CENTER;
    zoom = 5;
  }

  // Preview mode: show map but no markers
  const isPreviewMode = !hasValidActivities && fallbackCities.length > 0;

  return (
    <div className={styles.mapWrapper}>
      <MapContainer className={styles.map}>
        <SetViewOnMount center={center} zoom={zoom} />
        
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
        />
        
        {hasValidActivities && (
          <>
            <FitBounds activities={validActivities} />
            <FlyToSelected activity={selectedActivity} />
            
            {validActivities.map((activity) => (
              <Marker
                key={activity.id}
                position={[activity.location.lat!, activity.location.lng!]}
                eventHandlers={{
                  click: () => onActivitySelect?.(activity),
                }}
              >
                <Popup>
                  <div className={styles.popup}>
                    <strong>{activity.title}</strong>
                    <p>{activity.location.name}</p>
                    {activity.estimated_cost > 0 && (
                      <span className={styles.cost}>${activity.estimated_cost}</span>
                    )}
                  </div>
                </Popup>
              </Marker>
            ))}
          </>
        )}
      </MapContainer>
      
      {/* Preview mode overlay */}
      {isPreviewMode && (
        <div className={styles.previewOverlay}>
          <div className={styles.previewBadge}>
            📍 Preview Mode
          </div>
          <p>Locations will appear after you approve the trip</p>
        </div>
      )}
    </div>
  );
};
