import { useState, useEffect, useMemo, useCallback } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Trash2, MapPin, Loader } from 'lucide-react';
import { DaySection } from '../components/DaySection';
import { BudgetBar } from '../components/BudgetBar';
import { DiscoveryDrawer } from '../components/DiscoveryDrawer';
import { TripMap } from '../components/TripMap';
import { useTrips, useDiscovery } from '../hooks/useApi';
import type { Itinerary, Activity, DiscoveredPlace, DiscoveryType } from '../types';
import styles from './TripPage.module.css';

export const TripPage = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const tripId = searchParams.get('id');

  const { getTrip, deleteTrip, loading: tripLoading } = useTrips();
  const { discoverPlaces, starPlace, loading: discoveryLoading } = useDiscovery();

  const [trip, setTrip] = useState<Itinerary | null>(null);
  const [selectedActivity, setSelectedActivity] = useState<Activity | null>(null);
  const [discoveryOpen, setDiscoveryOpen] = useState(false);
  const [discoveryType, setDiscoveryType] = useState<DiscoveryType>('restaurant');
  const [places, setPlaces] = useState<DiscoveredPlace[]>([]);

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

  // Initial load
  useEffect(() => {
    loadTrip();
  }, [loadTrip]);

  // Poll for updates while geocoding
  useEffect(() => {
    if (!isGeocoding || !tripId) return;

    const interval = setInterval(() => {
      loadTrip();
    }, 2000); // Poll every 2 seconds

    return () => clearInterval(interval);
  }, [isGeocoding, tripId, loadTrip]);

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

  const handleDiscoveryClick = async (activity: Activity) => {
    // Check if activity has coordinates
    if (!activity.location.lat || !activity.location.lng) {
      if (isGeocoding) {
        alert('📍 This location is still being geocoded. Please wait a moment...');
      } else {
        alert('This activity doesn\'t have location coordinates for discovery.');
      }
      return;
    }
    
    if (!tripId) return;
    
    setSelectedActivity(activity);
    setDiscoveryOpen(true);
    setDiscoveryType('restaurant');
    
    const results = await discoverPlaces(tripId, activity.id, 'restaurant');
    setPlaces(results);
  };

  const handleTypeChange = async (type: DiscoveryType) => {
    if (!tripId || !selectedActivity) return;
    setDiscoveryType(type);
    const results = await discoverPlaces(tripId, selectedActivity.id, type);
    setPlaces(results);
  };

  const handleRegenerate = async () => {
    if (!tripId || !selectedActivity) return;
    const results = await discoverPlaces(tripId, selectedActivity.id, discoveryType, true);
    setPlaces(results);
  };

  const handleStar = async (placeId: string, starred: boolean) => {
    if (!tripId || !selectedActivity) return;
    const updated = await starPlace(tripId, selectedActivity.id, discoveryType, placeId, starred);
    if (updated) {
      setPlaces(prev => prev.map(p => p.id === placeId ? { ...p, starred } : p));
    }
  };

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
      <div className={styles.leftPanel}>
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
        {discoveryOpen && selectedActivity && (
          <DiscoveryDrawer
            activity={selectedActivity}
            places={places}
            isLoading={discoveryLoading}
            activeType={discoveryType}
            onTypeChange={handleTypeChange}
            onStar={handleStar}
            onRegenerate={handleRegenerate}
            onClose={() => setDiscoveryOpen(false)}
          />
        )}
      </div>
      </div> {/* End mainContent */}
    </div>
  );
};
