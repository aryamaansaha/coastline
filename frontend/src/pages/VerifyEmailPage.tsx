import { useState, useEffect } from 'react';
import { Link, useSearchParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import styles from './AuthPages.module.css';

export function VerifyEmailPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { isAuthenticated, refreshUser } = useAuth();

  const [isLoading, setIsLoading] = useState(true);
  const [isSuccess, setIsSuccess] = useState(false);
  const [error, setError] = useState('');

  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';
  const token = searchParams.get('token');

  useEffect(() => {
    const verifyEmail = async () => {
      if (!token) {
        setError('Invalid or missing verification token');
        setIsLoading(false);
        return;
      }

      try {
        const response = await fetch(`${API_BASE_URL}/api/auth/verify-email`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ token })
        });

        if (!response.ok) {
          const data = await response.json();
          throw new Error(data.detail || 'Email verification failed');
        }

        setIsSuccess(true);

        // Refresh user data if logged in (to update is_verified status)
        if (isAuthenticated) {
          await refreshUser();
        }

        // Redirect after 3 seconds - to trips if logged in, login if not
        setTimeout(() => {
          navigate(isAuthenticated ? '/trips' : '/login');
        }, 3000);
      } catch (err: any) {
        setError(err.message || 'Failed to verify email. The link may be expired or invalid.');
      } finally {
        setIsLoading(false);
      }
    };

    verifyEmail();
  }, [token, API_BASE_URL, navigate, isAuthenticated, refreshUser]);

  if (isLoading) {
    return (
      <div className={styles.authContainer}>
        <div className={styles.authCard}>
          <div className={styles.authHeader}>
            <h1 className={styles.authTitle}>Verifying Email</h1>
            <p className={styles.authSubtitle}>
              Please wait while we verify your email address...
            </p>
          </div>

          <div style={{ textAlign: 'center', padding: '20px' }}>
            <div style={{
              border: '4px solid #f3f4f6',
              borderTop: '4px solid #667eea',
              borderRadius: '50%',
              width: '40px',
              height: '40px',
              animation: 'spin 1s linear infinite',
              margin: '0 auto'
            }} />
          </div>
        </div>
      </div>
    );
  }

  if (isSuccess) {
    return (
      <div className={styles.authContainer}>
        <div className={styles.authCard}>
          <div className={styles.authHeader}>
            <h1 className={styles.authTitle}>Email Verified!</h1>
            <p className={styles.authSubtitle}>
              Your email has been successfully verified
            </p>
          </div>

          <div className={styles.successMessage}>
            {isAuthenticated ? 'Redirecting to your trips...' : 'Redirecting to login page...'}
          </div>

          <div className={styles.authFooter}>
            <Link to={isAuthenticated ? '/trips' : '/login'} className={styles.authLink}>
              {isAuthenticated ? 'Go to trips now' : 'Go to login now'}
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.authContainer}>
      <div className={styles.authCard}>
        <div className={styles.authHeader}>
          <h1 className={styles.authTitle}>Verification Failed</h1>
          <p className={styles.authSubtitle}>
            We couldn't verify your email address
          </p>
        </div>

        <div className={styles.errorMessage} style={{ padding: '12px', background: '#fee', borderRadius: '8px' }}>
          {error}
        </div>

        <div style={{ marginTop: '20px', textAlign: 'center', fontSize: '14px', color: '#666' }}>
          The verification link may have expired or already been used.
          You can request a new verification email after logging in.
        </div>

        <div className={styles.authFooter}>
          <Link to="/login" className={styles.authLink}>
            Go to login
          </Link>
        </div>
      </div>
    </div>
  );
}
