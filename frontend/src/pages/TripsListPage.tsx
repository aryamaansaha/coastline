import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Calendar, MapPin, Wallet, ChevronRight, Trash2, Loader, X } from 'lucide-react';
import { useTrips, type TripSummary } from '../hooks/useApi';
import { useTrip } from '../context/TripContext';
import { ConfirmModal } from '../components/ConfirmModal';
import { Logo } from '../components/Logo';
import { sessionStorage } from '../utils/sessionStorage';
import styles from './TripsListPage.module.css';

export const TripsListPage = () => {
  const navigate = useNavigate();
  const { listTrips, deleteTrip, loading } = useTrips();
  const { activeSession, hasActiveSession, resetTrip } = useTrip();
  const [trips, setTrips] = useState<TripSummary[]>([]);
  const [deleteModal, setDeleteModal] = useState<{ tripId: string; tripTitle: string; isError?: boolean } | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [elapsedTime, setElapsedTime] = useState('');

  useEffect(() => {
    listTrips().then(setTrips);
  }, [listTrips]);

  // Update elapsed time for in-progress card
  useEffect(() => {
    if (!activeSession?.startedAt) return;
    
    const update = () => {
      setElapsedTime(sessionStorage.getElapsedTime(activeSession.startedAt));
    };
    
    update();
    const interval = setInterval(update, 1000);
    return () => clearInterval(interval);
  }, [activeSession?.startedAt]);

  const handleDeleteClick = (e: React.MouseEvent, tripId: string, tripTitle: string) => {
    e.stopPropagation(); // Prevent card click navigation
    setDeleteModal({ tripId, tripTitle });
  };

  const handleDeleteConfirm = async () => {
    if (!deleteModal) return;
    
    // If it's an error modal, just close it
    if (deleteModal.isError) {
      setDeleteModal(null);
      return;
    }
    
    setIsDeleting(true);
    const success = await deleteTrip(deleteModal.tripId);
    setIsDeleting(false);
    
    if (success) {
      // Remove from local state
      setTrips(prev => prev.filter(t => t.trip_id !== deleteModal.tripId));
      setDeleteModal(null);
    } else {
      // Show error state in modal
      setDeleteModal({ ...deleteModal, isError: true });
    }
  };

  const handleDeleteCancel = () => {
    setDeleteModal(null);
  };

  const handleCancelGeneration = (e: React.MouseEvent) => {
    e.stopPropagation();
    sessionStorage.clear();
    resetTrip();
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '';
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'generating': return 'AI is planning...';
      case 'awaiting_approval': return 'Ready for review';
      case 'finalizing': return 'Finalizing trip...';
      default: return 'Processing...';
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.topBar}>
        <Logo size="md" />
      </div>
      
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

      {/* In-Progress Banner */}
      {hasActiveSession && activeSession && (
        <div 
          className={styles.inProgressCard}
          onClick={() => navigate('/new')}
        >
          <div className={styles.inProgressIcon}>
            <Loader size={24} className={styles.spinningLoader} />
          </div>
          <div className={styles.inProgressContent}>
            <div className={styles.inProgressHeader}>
              <span className={styles.inProgressTitle}>{activeSession.tripTitle}</span>
              <span className={styles.inProgressStatus}>
                {getStatusText(activeSession.status)}
              </span>
            </div>
            <div className={styles.inProgressMeta}>
              <span>Budget: ${activeSession.preferences.budget_limit.toLocaleString()}</span>
              <span>•</span>
              <span>{elapsedTime} elapsed</span>
            </div>
          </div>
          <div className={styles.inProgressActions}>
            <button 
              className={styles.cancelBtn}
              onClick={handleCancelGeneration}
              title="Cancel generation"
            >
              <X size={16} />
            </button>
            <ChevronRight size={20} className={styles.arrow} />
          </div>
        </div>
      )}

      {loading ? (
        <div className={styles.loading}>
          <div className={styles.spinner} />
          <p>Loading trips...</p>
        </div>
      ) : trips.length === 0 && !hasActiveSession ? (
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
                    onClick={(e) => handleDeleteClick(e, trip.trip_id, trip.trip_title)}
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

      {deleteModal && (
        <ConfirmModal
          isOpen={true}
          title={deleteModal.isError ? "Delete Failed" : "Delete Trip?"}
          message={
            deleteModal.isError
              ? "Failed to delete trip. Please try again."
              : `Are you sure you want to delete "${deleteModal.tripTitle}"? This action cannot be undone.`
          }
          confirmLabel={deleteModal.isError ? "OK" : "Delete"}
          cancelLabel={deleteModal.isError ? undefined : "Cancel"}
          onConfirm={handleDeleteConfirm}
          onCancel={handleDeleteCancel}
          variant={deleteModal.isError ? "warning" : "danger"}
        />
      )}
    </div>
  );
};
