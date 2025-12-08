import { useState, useMemo, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Check, Edit2, X } from 'lucide-react';
import { useTrip } from '../context/TripContext';
import { useTripStream } from '../hooks/useTripStream';
import { DaySection } from '../components/DaySection';
import { BudgetBar } from '../components/BudgetBar';
import { RevisionModal } from '../components/RevisionModal';
import { TripMap } from '../components/TripMap';
import type { Activity } from '../types';
import styles from './ReviewPage.module.css';

export const ReviewPage = () => {
  const navigate = useNavigate();
  const { preview, sessionId, resetTrip } = useTrip();
  const { submitDecision, cancelStream } = useTripStream();
  
  const [showRevisionModal, setShowRevisionModal] = useState(false);
  const [selectedActivity, setSelectedActivity] = useState<Activity | null>(null);

  if (!preview || !preview.itinerary) {
    return <div className={styles.error}>No preview available</div>;
  }

  const { itinerary, total_cost, budget_limit, budget_status, revision_count } = preview;

  // Flatten all activities for the map
  const allActivities = useMemo(() => {
    return itinerary.days.flatMap(day => day.activities);
  }, [itinerary]);

  // Extract unique cities for map fallback
  const cities = useMemo(() => {
    return [...new Set(itinerary.days.map(day => day.city))];
  }, [itinerary]);

  // Scroll to selected activity when clicking on map
  useEffect(() => {
    if (!selectedActivity) return;
    
    const element = document.querySelector(`[data-activity-id="${selectedActivity.id}"]`);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [selectedActivity]);

  const handleApprove = () => {
    if (!sessionId) return;
    submitDecision('approve');
  };

  const handleRevise = (feedback: string, newBudget?: number) => {
    if (!sessionId) return;
    submitDecision('revise', feedback, newBudget);
    setShowRevisionModal(false);
  };

  const handleCancel = async () => {
    if (confirm('Are you sure you want to cancel this trip?')) {
      // Abort any active SSE connection first
      cancelStream();
      
      // Delete backend session if it exists (cleanup)
      if (sessionId) {
        try {
          await fetch(`/api/trip/session/${sessionId}`, { method: 'DELETE' });
        } catch (err) {
          console.error('Failed to delete session:', err);
          // Continue anyway - frontend cleanup is more important
        }
      }
      
      // Clear frontend state and navigate away
      resetTrip();
      navigate('/'); // Navigate to trips list
    }
  };

  return (
    <div className={styles.container}>
      {/* Left Panel - Itinerary */}
      <div className={styles.leftPanel}>
        <div className={styles.header}>
          <div className={styles.titleArea}>
            <span className={styles.badge}>
              {revision_count > 0 ? `Revision #${revision_count}` : 'Review Draft'}
            </span>
            <h1 className={styles.title}>{itinerary.trip_title}</h1>
            <p className={styles.meta}>
              {itinerary.days.length} days • {itinerary.days.map(d => d.city).filter((v, i, a) => a.indexOf(v) === i).join(' → ')}
            </p>
          </div>
          
          <BudgetBar totalCost={total_cost} budgetLimit={budget_limit} />
        </div>

        <div className={styles.scrollArea}>
          {itinerary.days.map((day, index) => (
            <DaySection
              key={day.id || `day-${day.day_number}-${index}`}
              day={day}
              highlightedActivityId={selectedActivity?.id}
              showDiscovery={false}
              onActivityClick={(activity) => setSelectedActivity(activity)}
            />
          ))}
        </div>

        {/* Action Bar */}
        <div className={styles.actionBar}>
          <button className={styles.btnDanger} onClick={handleCancel}>
            <X size={18} /> Cancel
          </button>
          <button className={styles.btnSecondary} onClick={() => setShowRevisionModal(true)}>
            <Edit2 size={18} /> Revise
          </button>
          <button className={styles.btnPrimary} onClick={handleApprove}>
            <Check size={18} /> Approve Trip
          </button>
        </div>
      </div>

      {/* Right Panel - Map */}
      <div className={styles.rightPanel}>
        <TripMap
          activities={allActivities}
          selectedActivity={selectedActivity}
          onActivitySelect={setSelectedActivity}
          fallbackCities={cities}
        />
      </div>

      {/* Revision Modal */}
      {showRevisionModal && (
        <RevisionModal
          currentBudget={budget_limit}
          onSubmit={handleRevise}
          onCancel={() => setShowRevisionModal(false)}
        />
      )}
    </div>
  );
};
