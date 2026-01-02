import { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import styles from './SignupModal.module.css';

interface SignupModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  tripId: string | null;
}

type Tab = 'signup' | 'login';

export function SignupModal({ isOpen, onClose, onSuccess, tripId }: SignupModalProps) {
  const { login, signup } = useAuth();

  const [activeTab, setActiveTab] = useState<Tab>('signup');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  if (!isOpen) return null;

  const validatePassword = (pwd: string): string | null => {
    if (pwd.length < 8) {
      return 'Password must be at least 8 characters';
    }
    if (!/[A-Z]/.test(pwd)) {
      return 'Password must contain at least one uppercase letter';
    }
    if (!/[a-z]/.test(pwd)) {
      return 'Password must contain at least one lowercase letter';
    }
    if (!/[0-9]/.test(pwd)) {
      return 'Password must contain at least one number';
    }
    return null;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (activeTab === 'signup') {
      // Validate passwords match
      if (password !== confirmPassword) {
        setError('Passwords do not match');
        return;
      }

      // Validate password strength
      const passwordError = validatePassword(password);
      if (passwordError) {
        setError(passwordError);
        return;
      }
    }

    setIsLoading(true);

    try {
      if (activeTab === 'signup') {
        await signup(email, password);
      } else {
        await login(email, password);
      }

      // Success - call onSuccess to claim trip
      onSuccess();
    } catch (err: any) {
      setError(err.message || `${activeTab === 'signup' ? 'Signup' : 'Login'} failed. Please try again.`);
      setIsLoading(false);
    }
  };

  const handleOverlayClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  return (
    <div className={styles.modalOverlay} onClick={handleOverlayClick}>
      <div className={styles.modalCard}>
        <button className={styles.closeButton} onClick={onClose}>
          ×
        </button>

        <div className={styles.modalHeader}>
          <h2 className={styles.modalTitle}>Save Your Trip</h2>
          <p className={styles.modalSubtitle}>
            {tripId ? 'Create an account or log in to save this trip' : 'Create an account to save your trips'}
          </p>
        </div>

        <div className={styles.tabs}>
          <button
            className={`${styles.tab} ${activeTab === 'signup' ? styles.active : ''}`}
            onClick={() => {
              setActiveTab('signup');
              setError('');
            }}
          >
            Sign Up
          </button>
          <button
            className={`${styles.tab} ${activeTab === 'login' ? styles.active : ''}`}
            onClick={() => {
              setActiveTab('login');
              setError('');
            }}
          >
            Log In
          </button>
        </div>

        <form onSubmit={handleSubmit} className={styles.form}>
          {error && (
            <div className={styles.errorMessage}>
              {error}
            </div>
          )}

          <div className={styles.formGroup}>
            <label htmlFor="email" className={styles.formLabel}>
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className={styles.formInput}
              required
              autoComplete="email"
              disabled={isLoading}
            />
          </div>

          <div className={styles.formGroup}>
            <label htmlFor="password" className={styles.formLabel}>
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className={styles.formInput}
              required
              autoComplete={activeTab === 'signup' ? 'new-password' : 'current-password'}
              disabled={isLoading}
            />
            {activeTab === 'signup' && (
              <div className={styles.passwordHints}>
                Password must contain:
                <ul>
                  <li>At least 8 characters</li>
                  <li>One uppercase letter</li>
                  <li>One lowercase letter</li>
                  <li>One number</li>
                </ul>
              </div>
            )}
          </div>

          {activeTab === 'signup' && (
            <div className={styles.formGroup}>
              <label htmlFor="confirmPassword" className={styles.formLabel}>
                Confirm Password
              </label>
              <input
                id="confirmPassword"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className={styles.formInput}
                required
                autoComplete="new-password"
                disabled={isLoading}
              />
            </div>
          )}

          <button
            type="submit"
            className={styles.submitButton}
            disabled={isLoading}
          >
            {isLoading
              ? (activeTab === 'signup' ? 'Creating account...' : 'Logging in...')
              : (activeTab === 'signup' ? 'Sign Up & Save Trip' : 'Log In & Save Trip')
            }
          </button>
        </form>
      </div>
    </div>
  );
}
