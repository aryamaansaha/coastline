import { useState, useEffect, useMemo, useCallback } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Trash2, MapPin, Loader, Map, List } from 'lucide-react';
import { DaySection } from '../components/DaySection';
import { BudgetBar } from '../components/BudgetBar';
import { DiscoveryDrawer } from '../components/DiscoveryDrawer';
import { TripMap } from '../components/TripMap';
import { useTrips, useDiscovery } from '../hooks/useApi';
import type { Itinerary, Activity, DiscoveredPlace, DiscoveryType } from '../types';
import styles from './TripPage.module.css';

// Type for cached discoveries (activity -> type -> places)
type DiscoveryCache = Record<string, Partial<Record<DiscoveryType, DiscoveredPlace[]>>>;

export const TripPage = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const tripId = searchParams.get('id');

  const { getTrip, deleteTrip, loading: tripLoading } = useTrips();
  const { discoverPlaces, starPlace, getAllDiscoveries } = useDiscovery();

  const [trip, setTrip] = useState<Itinerary | null>(null);
  const [selectedActivity, setSelectedActivity] = useState<Activity | null>(null);
  const [discoveryOpen, setDiscoveryOpen] = useState(false);
  const [mobileView, setMobileView] = useState<'itinerary' | 'map'>('itinerary');
  
  // Cache of discoveries: { activityId: { restaurant: [...], bar: [...], ... } }
  const [discoveryCache, setDiscoveryCache] = useState<DiscoveryCache>({});

  // Check if geocoding is still in progress
  const isGeocoding = useMemo(() => {
    if (!trip?.geocoding_status) return false;
    return trip.geocoding_status.status === 'pending' || trip.geocoding_status.status === 'in_progress';
  }, [trip?.geocoding_status]);

  const geocodingProgress = useMemo(() => {
    if (!trip?.geocoding_status) return null;
    const { geocoded_activities, total_activities } = trip.geocoding_status;
    return {
      percent: total_activities > 0 ? Math.round((geocoded_activities / total_activities) * 100) : 0,
      geocoded: geocoded_activities,
      total: total_activities
    };
  }, [trip?.geocoding_status]);

  // Load trip
  const loadTrip = useCallback(async () => {
    if (!tripId) return;
    const data = await getTrip(tripId);
    if (data) setTrip(data);
  }, [tripId, getTrip]);

  // Load all existing discoveries for this trip
  const loadDiscoveries = useCallback(async () => {
    if (!tripId) return;
    const discoveries = await getAllDiscoveries(tripId);
    
    // Convert array of discoveries to our cache format
    const cache: DiscoveryCache = {};
    for (const disc of discoveries) {
      const activityId = disc.activity_id;
      const discType = disc.discovery_type as DiscoveryType;
      if (!cache[activityId]) cache[activityId] = {};
      cache[activityId][discType] = disc.places || [];
    }
    setDiscoveryCache(cache);
  }, [tripId, getAllDiscoveries]);

  // Initial load
  useEffect(() => {
    loadTrip();
    loadDiscoveries();
  }, [loadTrip, loadDiscoveries]);

  // Poll for updates while geocoding
  useEffect(() => {
    if (!isGeocoding || !tripId) return;

    const interval = setInterval(() => {
      loadTrip();
    }, 2000);

    return () => clearInterval(interval);
  }, [isGeocoding, tripId, loadTrip]);

  // Scroll to selected activity when clicking on map
  useEffect(() => {
    if (!selectedActivity) return;
    
    const element = document.querySelector(`[data-activity-id="${selectedActivity.id}"]`);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [selectedActivity]);

  // Flatten all activities for the map
  const allActivities = useMemo(() => {
    if (!trip) return [];
    return trip.days.flatMap(day => day.activities);
  }, [trip]);

  // Extract cities for map fallback
  const cities = useMemo(() => {
    if (!trip) return [];
    return [...new Set(trip.days.map(d => d.city))];
  }, [trip]);

  // Calculate total cost
  const totalCost = useMemo(() => {
    return allActivities.reduce((sum, act) => sum + act.estimated_cost, 0);
  }, [allActivities]);

  // Handle opening the discovery drawer
  const handleDiscoveryClick = (activity: Activity) => {
    // Check if activity has coordinates
    if (!activity.location.lat || !activity.location.lng) {
      if (isGeocoding) {
        alert('📍 This location is still being geocoded. Please wait a moment...');
      } else {
        alert('This activity doesn\'t have location coordinates for discovery.');
      }
      return;
    }
    
    setSelectedActivity(activity);
    setDiscoveryOpen(true);
    // No API call here - drawer will handle it when user clicks "Find"
  };

  // Discovery callback for the drawer
  const handleDiscover = useCallback(async (
    activityId: string, 
    type: DiscoveryType, 
    regenerate: boolean
  ): Promise<DiscoveredPlace[]> => {
    if (!tripId) return [];
    
    const results = await discoverPlaces(tripId, activityId, type, regenerate);
    
    // Update cache
    setDiscoveryCache(prev => ({
      ...prev,
      [activityId]: {
        ...prev[activityId],
        [type]: results
      }
    }));
    
    return results;
  }, [tripId, discoverPlaces]);

  // Star callback for the drawer
  const handleStar = useCallback(async (
    activityId: string,
    type: DiscoveryType,
    placeId: string,
    starred: boolean
  ): Promise<void> => {
    if (!tripId) return;
    
    await starPlace(tripId, activityId, type, placeId, starred);
    
    // Update cache
    setDiscoveryCache(prev => ({
      ...prev,
      [activityId]: {
        ...prev[activityId],
        [type]: (prev[activityId]?.[type] || []).map(p =>
          p.id === placeId ? { ...p, starred } : p
        )
      }
    }));
  }, [tripId, starPlace]);

  const handleDelete = async () => {
    if (!tripId) return;
    if (confirm('Are you sure you want to delete this trip? This cannot be undone.')) {
      const success = await deleteTrip(tripId);
      if (success) {
        navigate('/');
      }
    }
  };

  if (tripLoading && !trip) {
    return (
      <div className={styles.loading}>
        <div className={styles.spinner} />
        <p>Loading trip...</p>
      </div>
    );
  }

  if (!trip) {
    return (
      <div className={styles.notFound}>
        <h2>Trip not found</h2>
        <button onClick={() => navigate('/')}>← Back to Home</button>
      </div>
    );
  }

  // Get cached discoveries for selected activity
  const selectedActivityDiscoveries = selectedActivity 
    ? discoveryCache[selectedActivity.id] || {}
    : {};

  return (
    <div className={styles.container}>
      {/* Geocoding Banner */}
      {isGeocoding && geocodingProgress && (
        <div className={styles.geocodingBanner}>
          <Loader size={16} className={styles.spinnerInline} />
          <span>
            <MapPin size={14} /> Geocoding locations... {geocodingProgress.geocoded}/{geocodingProgress.total} ({geocodingProgress.percent}%)
          </span>
        </div>
      )}

      <div className={styles.mainContent}>
        {/* Left Panel */}
        <div className={`${styles.leftPanel} ${mobileView === 'map' ? styles.hidden : ''}`}>
          <div className={styles.header}>
            <div className={styles.headerTop}>
              <button className={styles.backBtn} onClick={() => navigate('/')}>
                <ArrowLeft size={18} /> Back
              </button>
              <button className={styles.deleteBtn} onClick={handleDelete}>
                <Trash2 size={16} />
              </button>
            </div>
            
            <h1 className={styles.title}>{trip.trip_title}</h1>
            <p className={styles.meta}>
              {trip.days.length} days • {trip.days.map(d => d.city).filter((v, i, a) => a.indexOf(v) === i).join(' → ')}
            </p>
            
            <BudgetBar totalCost={totalCost} budgetLimit={trip.budget_limit} />
          </div>

          <div className={styles.scrollArea}>
            {trip.days.map((day, index) => (
              <DaySection
                key={day.id || `day-${day.day_number}-${index}`}
                day={day}
                highlightedActivityId={selectedActivity?.id}
                showDiscovery={true}
                onDiscoveryClick={handleDiscoveryClick}
                onActivityClick={(activity) => {
                  setSelectedActivity(activity);
                  setDiscoveryOpen(false);
                }}
              />
            ))}
          </div>
        </div>

        {/* Right Panel - Map + Discovery */}
        <div className={styles.rightPanel}>
          <TripMap
            activities={allActivities}
            selectedActivity={selectedActivity}
            onActivitySelect={(activity) => {
              setSelectedActivity(activity);
              setDiscoveryOpen(false);
            }}
            fallbackCities={cities}
          />
          
          {/* Discovery Drawer overlays the map */}
          {discoveryOpen && selectedActivity && tripId && (
            <DiscoveryDrawer
              activity={selectedActivity}
              tripId={tripId}
              onClose={() => setDiscoveryOpen(false)}
              onDiscover={handleDiscover}
              onStar={handleStar}
              discoveries={selectedActivityDiscoveries}
            />
          )}
        </div>

        {/* Mobile View Toggle */}
        <div className={styles.mobileToggle}>
          <button 
            className={mobileView === 'itinerary' ? styles.active : ''}
            onClick={() => setMobileView('itinerary')}
          >
            <List size={16} /> Itinerary
          </button>
          <button 
            className={mobileView === 'map' ? styles.active : ''}
            onClick={() => setMobileView('map')}
          >
            <Map size={16} /> Map
          </button>
        </div>
      </div>
    </div>
  );
};
