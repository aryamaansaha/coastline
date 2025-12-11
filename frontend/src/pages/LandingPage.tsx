import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTrip } from '../context/TripContext';
import { useTripStream } from '../hooks/useTripStream';
import type { TripPreferences } from '../types';
import { Plane, Calendar, Wallet, MapPin, X, ArrowLeft, Plus } from 'lucide-react';
import { Logo } from '../components/Logo';
import styles from './LandingPage.module.css';

export const LandingPage = () => {
  const navigate = useNavigate();
  const { setPreferences } = useTrip();
  const { startGeneration } = useTripStream();

  // Local state for form
  const [destinations, setDestinations] = useState<string[]>(['London', 'Paris']);
  const [currentDest, setCurrentDest] = useState('');
  
  const [startDate, setStartDate] = useState('2026-01-10');
  const [endDate, setEndDate] = useState('2026-01-18');
  const [budget, setBudget] = useState(3000);
  const [origin, setOrigin] = useState('New York');

  const addDestination = () => {
    const trimmed = currentDest.trim();
    if (trimmed && !destinations.some(d => d.toLowerCase() === trimmed.toLowerCase())) {
      setDestinations([...destinations, trimmed]);
      setCurrentDest('');
    }
  };

  const removeDestination = (dest: string) => {
    setDestinations(destinations.filter(d => d !== dest));
  };

  const handleSubmit = () => {
    if (destinations.length === 0) {
      alert('Please add at least one destination');
      return;
    }
    
    const prefs: TripPreferences = {
      destinations,
      start_date: new Date(startDate).toISOString(),
      end_date: new Date(endDate).toISOString(),
      budget_limit: budget,
      origin
    };

    setPreferences(prefs);
    startGeneration(prefs);
  };

  return (
    <div className={styles.container}>
      <div className={styles.card}>
        <div className={styles.backLink} onClick={() => navigate('/')}>
          <ArrowLeft size={16} /> Back to trips
        </div>
        
        <div className={styles.logoWrapper}>
          <Logo size="lg" />
        </div>
        
        <h1 className={styles.title}>Plan your next escape.</h1>
        <p className={styles.subtitle}>AI-powered itineraries, tailored to your budget.</p>

        {/* Destinations Input */}
        <div className={styles.group}>
          <label><MapPin size={16}/> Destinations</label>
          <div className={styles.chipContainer}>
            {destinations.map(dest => (
              <span key={dest} className={styles.chip}>
                {dest}
                <button onClick={() => removeDestination(dest)} type="button">
                  <X size={12}/>
                </button>
              </span>
            ))}
            <input 
              type="text" 
              value={currentDest}
              onChange={(e) => setCurrentDest(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === 'Go' || e.keyCode === 13) {
                  e.preventDefault();
                  addDestination();
                  // Blur the input to dismiss mobile keyboard
                  (e.target as HTMLInputElement).blur();
                }
              }}
              onBlur={() => {
                // Add destination when user finishes typing (mobile-friendly)
                if (currentDest.trim()) {
                  addDestination();
                }
              }}
              placeholder="Add city..."
              className={styles.chipInput}
            />
            {currentDest.trim() && (
              <button
                type="button"
                onClick={(e) => {
                  e.preventDefault();
                  addDestination();
                }}
                className={styles.addBtn}
                aria-label="Add destination"
              >
                <Plus size={16} />
              </button>
            )}
          </div>
        </div>

        {/* Dates */}
        <div className={styles.row}>
          <div className={styles.group}>
            <label><Calendar size={16}/> Start</label>
            <input 
              type="date" 
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className={styles.input}
            />
          </div>
          <div className={styles.group}>
            <label><Calendar size={16}/> End</label>
            <input 
              type="date" 
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className={styles.input}
            />
          </div>
        </div>

        {/* Budget & Origin */}
        <div className={styles.row}>
          <div className={styles.group}>
            <label><Wallet size={16}/> Budget (USD)</label>
            <input 
              type="number" 
              value={budget}
              onChange={(e) => setBudget(Number(e.target.value))}
              className={styles.input}
            />
          </div>
          <div className={styles.group}>
            <label><Plane size={16}/> From</label>
            <input 
              type="text" 
              value={origin}
              onChange={(e) => setOrigin(e.target.value)}
              className={styles.input}
            />
          </div>
        </div>

        <button className={styles.submitBtn} onClick={handleSubmit}>
          Start Planning →
        </button>
      </div>
    </div>
  );
};
