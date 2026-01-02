import { BrowserRouter, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import { useEffect, useRef } from 'react';
import { useTrip } from './context/TripContext';
import { useAuth } from './context/AuthContext';
import { useTrips } from './hooks/useApi';
import { LandingPage } from './pages/LandingPage';
import { LoadingPage } from './pages/LoadingPage';
import { ReviewPage } from './pages/ReviewPage';
import { TripPage } from './pages/TripPage';
import { TripsListPage } from './pages/TripsListPage';
import { LoginPage } from './pages/LoginPage';
import { SignupPage } from './pages/SignupPage';
import { ForgotPasswordPage } from './pages/ForgotPasswordPage';
import { ResetPasswordPage } from './pages/ResetPasswordPage';
import { VerifyEmailPage } from './pages/VerifyEmailPage';
import { PrivateRoute } from './components/PrivateRoute';
import { SignupModal } from './components/SignupModal';

// Main content component that handles the planning flow state
function PlanningFlow() {
  const navigate = useNavigate();
  const { isStreaming, preview, finalTripId, streamError, resetTrip, sessionId, hasActiveSession, restoreSession, showSignupModal, setShowSignupModal, pendingTripId, setPendingTripId } = useTrip();
  const { isAuthenticated } = useAuth();
  const { claimTrip } = useTrips();
  const hasCheckedSession = useRef(false);

  // Check for existing session on mount
  useEffect(() => {
    if (!hasCheckedSession.current && !isStreaming && !preview && !finalTripId) {
      hasCheckedSession.current = true;
      const saved = restoreSession();
      if (saved) {
        console.log('Restored session from localStorage:', saved);
      }
    }
  }, [restoreSession, isStreaming, preview, finalTripId]);

  // Navigate to trip page when generation completes
  useEffect(() => {
    if (finalTripId) {
      console.log('Trip generation complete, navigating to:', finalTripId);
      navigate(`/trip?id=${finalTripId}`, { replace: true });
      // Reset state after navigation completes
      setTimeout(() => {
        resetTrip();
      }, 200);
    }
  }, [finalTripId, navigate, resetTrip]);

  // Safety check: Clear stale previews (preview without active session)
  useEffect(() => {
    if (preview && !sessionId && !isStreaming) {
      // Stale preview detected - clear it
      console.log('Clearing stale preview');
      resetTrip();
    }
  }, [preview, sessionId, isStreaming, resetTrip]);

  // Guest flow: Show signup modal when guest completes trip
  useEffect(() => {
    if (finalTripId && !isAuthenticated) {
      console.log('Guest trip completed, showing signup modal');
      setPendingTripId(finalTripId);
      setShowSignupModal(true);
    }
  }, [finalTripId, isAuthenticated, setPendingTripId, setShowSignupModal]);

  // Handle signup success
  const handleSignupSuccess = async () => {
    if (pendingTripId) {
      console.log('Claiming trip:', pendingTripId);
      const success = await claimTrip(pendingTripId);
      if (success) {
        console.log('Trip claimed successfully');
      }
    }
    setShowSignupModal(false);
    setPendingTripId(null);
    // Navigate to trip page
    if (pendingTripId) {
      navigate(`/trip?id=${pendingTripId}`, { replace: true });
    }
    resetTrip();
  };

  // Handle signup modal close (user dismisses)
  const handleSignupClose = () => {
    setShowSignupModal(false);
    // Don't reset pendingTripId yet - user might still want to view the trip
    // Navigation will happen naturally from the existing finalTripId effect
  };

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

  // Error State
  if (streamError) {
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
        <p style={{ color: '#64748b', marginBottom: '24px' }}>{streamError}</p>
        <button 
          onClick={resetTrip}
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

  // Loading / Agent Working (including restored sessions)
  if (isStreaming || hasActiveSession) {
    return <LoadingPage />;
  }

  // Default: Landing (new trip form)
  return (
    <>
      <LandingPage />
      <SignupModal
        isOpen={showSignupModal}
        onClose={handleSignupClose}
        onSuccess={handleSignupSuccess}
        tripId={pendingTripId}
      />
    </>
  );
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Auth Routes */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />
        <Route path="/verify-email" element={<VerifyEmailPage />} />

        {/* Landing Page - Public (guest access) */}
        <Route path="/" element={<PlanningFlow />} />

        {/* My Trips - Protected */}
        <Route path="/trips" element={
          <PrivateRoute>
            <TripsListPage />
          </PrivateRoute>
        } />

        {/* New Trip Planning Flow - Public (guest access) */}
        <Route path="/new" element={<PlanningFlow />} />

        {/* View Saved Trip - Protected */}
        <Route path="/trip" element={
          <PrivateRoute>
            <TripPage />
          </PrivateRoute>
        } />

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
