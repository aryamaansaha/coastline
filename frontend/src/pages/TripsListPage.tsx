import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Calendar, MapPin, Wallet, ChevronRight, Trash2 } from 'lucide-react';
import { useTrips, type TripSummary } from '../hooks/useApi';
import styles from './TripsListPage.module.css';

export const TripsListPage = () => {
  const navigate = useNavigate();
  const { listTrips, deleteTrip, loading } = useTrips();
  const [trips, setTrips] = useState<TripSummary[]>([]);

  useEffect(() => {
    listTrips().then(setTrips);
  }, [listTrips]);

  const handleDelete = async (e: React.MouseEvent, tripId: string, tripTitle: string) => {
    e.stopPropagation(); // Prevent card click navigation
    if (confirm(`Are you sure you want to delete "${tripTitle}"? This cannot be undone.`)) {
      const success = await deleteTrip(tripId);
      if (success) {
        // Remove from local state
        setTrips(prev => prev.filter(t => t.trip_id !== tripId));
      } else {
        alert('Failed to delete trip. Please try again.');
      }
    }
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '';
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  };

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <div>
          <h1 className={styles.title}>Your Trips</h1>
          <p className={styles.subtitle}>
            {trips.length === 0 
              ? 'No trips yet. Start planning your first adventure!'
              : `${trips.length} trip${trips.length > 1 ? 's' : ''} planned`
            }
          </p>
        </div>
        <button className={styles.newTripBtn} onClick={() => navigate('/new')}>
          <Plus size={18} /> New Trip
        </button>
      </div>

      {loading ? (
        <div className={styles.loading}>
          <div className={styles.spinner} />
          <p>Loading trips...</p>
        </div>
      ) : trips.length === 0 ? (
        <div className={styles.empty}>
          <div className={styles.emptyIcon}>🌴</div>
          <h3>No trips yet</h3>
          <p>Create your first AI-powered itinerary</p>
          <button className={styles.createBtn} onClick={() => navigate('/new')}>
            Start Planning
          </button>
        </div>
      ) : (
        <div className={styles.grid}>
          {trips.map(trip => (
            <div 
              key={trip.trip_id} 
              className={styles.card}
              onClick={() => navigate(`/trip?id=${trip.trip_id}`)}
            >
              <div className={styles.cardHeader}>
                <h3>{trip.trip_title}</h3>
                <div className={styles.cardActions}>
                  <button
                    className={styles.deleteBtn}
                    onClick={(e) => handleDelete(e, trip.trip_id, trip.trip_title)}
                    title="Delete trip"
                  >
                    <Trash2 size={16} />
                  </button>
                  <ChevronRight size={18} className={styles.arrow} />
                </div>
              </div>
              
              <div className={styles.cardMeta}>
                <span className={styles.metaItem}>
                  <MapPin size={14} />
                  {trip.destinations.join(' → ')}
                </span>
                <span className={styles.metaItem}>
                  <Calendar size={14} />
                  {trip.num_days} days
                </span>
                <span className={styles.metaItem}>
                  <Wallet size={14} />
                  ${trip.budget_limit.toLocaleString()}
                </span>
              </div>
              
              {trip.created_at && (
                <div className={styles.cardFooter}>
                  Created {formatDate(trip.created_at)}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

