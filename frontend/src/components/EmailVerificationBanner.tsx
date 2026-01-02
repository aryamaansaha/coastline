import { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import styles from './EmailVerificationBanner.module.css';

export function EmailVerificationBanner() {
  const { user, token } = useAuth();
  const [isDismissed, setIsDismissed] = useState(false);
  const [isResending, setIsResending] = useState(false);
  const [resendStatus, setResendStatus] = useState<'success' | 'error' | null>(null);

  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8008';

  // Don't show banner if user is verified, not authenticated, or dismissed
  if (!user || user.is_verified || isDismissed) {
    return null;
  }

  const handleResend = async () => {
    setIsResending(true);
    setResendStatus(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/resend-verification`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        setResendStatus('success');
        setTimeout(() => setResendStatus(null), 5000);
      } else {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to resend');
      }
    } catch (err) {
      setResendStatus('error');
      setTimeout(() => setResendStatus(null), 5000);
    } finally {
      setIsResending(false);
    }
  };

  return (
    <div className={styles.banner}>
      <div className={styles.content}>
        <span className={styles.icon}>⚠️</span>
        <div className={styles.message}>
          <strong>Verify your email</strong> to unlock all features
        </div>
      </div>

      <div className={styles.actions}>
        {resendStatus === 'success' && (
          <div className={styles.successMessage}>
            Email sent! Check your inbox.
          </div>
        )}

        {resendStatus === 'error' && (
          <div className={styles.errorMessage}>
            Failed to send. Try again later.
          </div>
        )}

        {!resendStatus && (
          <button
            onClick={handleResend}
            disabled={isResending}
            className={styles.resendButton}
          >
            {isResending ? 'Sending...' : 'Resend Email'}
          </button>
        )}

        <button
          onClick={() => setIsDismissed(true)}
          className={styles.closeButton}
          aria-label="Dismiss"
        >
          ×
        </button>
      </div>
    </div>
  );
}
