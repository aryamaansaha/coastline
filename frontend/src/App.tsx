import { BrowserRouter, Routes, Route, Navigate, useNavigate, useSearchParams } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { useTrip } from './context/TripContext';
import { useTripStream } from './hooks/useTripStream';
import { LandingPage } from './pages/LandingPage';
import { LoadingPage } from './pages/LoadingPage';
import { ReviewPage } from './pages/ReviewPage';
import { TripPage } from './pages/TripPage';
import { TripsListPage } from './pages/TripsListPage';

// Main content component that handles the planning flow state
function PlanningFlow() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { 
    isStreaming, 
    preview, 
    finalTripId, 
    streamError, 
    resetTrip, 
    sessionId,
    activeSession,
    setPreferences
  } = useTrip();
  const { reconnectToSession } = useTripStream();
  
  const [isReconnecting, setIsReconnecting] = useState(false);
  const [reconnectError, setReconnectError] = useState<string | null>(null);

  // Handle resume query param - reconnect to existing session
  useEffect(() => {
    const shouldResume = searchParams.get('resume') === 'true';
    
    if (shouldResume && activeSession && activeSession.sessionId !== 'pending') {
      setIsReconnecting(true);
      setReconnectError(null);
      
      reconnectToSession(activeSession).then((result) => {
        setIsReconnecting(false);
        
        switch (result) {
          case 'complete':
            // Trip completed while away - finalTripId should be set, will redirect
            break;
          case 'review':
            // Ready for review - preview should be set
            break;
          case 'streaming':
            // Still processing - show loading
            break;
          case 'not_found':
            setReconnectError('Session expired or not found. Please start a new trip.');
            break;
          case 'error':
            setReconnectError('Failed to reconnect. Please start a new trip.');
            break;
        }
        
        // Clear the resume param from URL
        navigate('/new', { replace: true });
      });
    } else if (shouldResume && activeSession?.sessionId === 'pending') {
      // Session still initializing - restore preferences and show loading
      setPreferences(activeSession.preferences);
      navigate('/new', { replace: true });
    }
  }, [searchParams, activeSession, reconnectToSession, navigate, setPreferences]);

  // Navigate to trip page when generation completes
  useEffect(() => {
    if (finalTripId) {
      navigate(`/trip?id=${finalTripId}`, { replace: true });
      // Reset state after navigation completes
      setTimeout(() => {
        resetTrip();
      }, 200);
    }
  }, [finalTripId, navigate, resetTrip]);

  // Safety check: Clear stale previews (preview without active session)
  useEffect(() => {
    if (preview && !sessionId && !isStreaming && !isReconnecting) {
      // Stale preview detected - clear it
      console.log('Clearing stale preview');
      resetTrip();
    }
  }, [preview, sessionId, isStreaming, isReconnecting, resetTrip]);

  // Reconnecting state
  if (isReconnecting) {
    return (
      <div style={{ 
        display: 'flex', 
        flexDirection: 'column',
        alignItems: 'center', 
        justifyContent: 'center', 
        height: '100vh' 
      }}>
        <div style={{
          width: '32px',
          height: '32px',
          border: '3px solid #e2e8f0',
          borderTopColor: '#3b82f6',
          borderRadius: '50%',
          animation: 'spin 0.8s linear infinite',
          marginBottom: '16px'
        }} />
        <p style={{ color: '#64748b' }}>Reconnecting to your trip...</p>
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  // If trip is complete, show loading while navigating
  if (finalTripId) {
    return (
      <div style={{ 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center', 
        height: '100vh' 
      }}>
        <p>Redirecting to your trip...</p>
      </div>
    );
  }

  // Error State (including reconnect errors)
  if (streamError || reconnectError) {
    return (
      <div style={{ 
        display: 'flex', 
        flexDirection: 'column',
        alignItems: 'center', 
        justifyContent: 'center', 
        height: '100vh',
        padding: '40px',
        textAlign: 'center'
      }}>
        <h2 style={{ color: '#ef4444', marginBottom: '16px' }}>Something went wrong</h2>
        <p style={{ color: '#64748b', marginBottom: '24px' }}>{streamError || reconnectError}</p>
        <button 
          onClick={() => {
            setReconnectError(null);
            resetTrip();
          }}
          style={{
            padding: '12px 24px',
            background: '#0f172a',
            color: 'white',
            border: 'none',
            borderRadius: '8px',
            cursor: 'pointer',
            fontWeight: 500
          }}
        >
          Try Again
        </button>
      </div>
    );
  }

  // Review Mode (HITL)
  if (preview) {
    return <ReviewPage />;
  }

  // Loading / Agent Working
  if (isStreaming) {
    return <LoadingPage />;
  }

  // Default: Landing (new trip form)
  return <LandingPage />;
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Home / My Trips */}
        <Route path="/" element={<TripsListPage />} />
        
        {/* New Trip Planning Flow */}
        <Route path="/new" element={<PlanningFlow />} />
        
        {/* View Saved Trip */}
        <Route path="/trip" element={<TripPage />} />
        
        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
