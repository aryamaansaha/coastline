import { useState } from 'react';
import { Link } from 'react-router-dom';
import styles from './AuthPages.module.css';

export function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);

  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      await fetch(`${API_BASE_URL}/api/auth/request-password-reset`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ email })
      });

      // Always show success to prevent email enumeration
      setIsSubmitted(true);
    } catch (err) {
      // Still show success even on error to prevent enumeration
      setIsSubmitted(true);
    } finally {
      setIsLoading(false);
    }
  };

  if (isSubmitted) {
    return (
      <div className={styles.authContainer}>
        <div className={styles.authCard}>
          <div className={styles.authHeader}>
            <h1 className={styles.authTitle}>Check Your Email</h1>
            <p className={styles.authSubtitle}>
              If an account exists with {email}, you will receive a password reset link shortly.
            </p>
          </div>

          <div className={styles.successMessage}>
            Password reset instructions have been sent!
          </div>

          <div className={styles.authFooter}>
            Remember your password?
            <Link to="/login" className={styles.authLink}>
              Log in
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
          <h1 className={styles.authTitle}>Reset Password</h1>
          <p className={styles.authSubtitle}>
            Enter your email and we'll send you a reset link
          </p>
        </div>

        <form onSubmit={handleSubmit} className={styles.authForm}>
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

          <button
            type="submit"
            className={styles.submitButton}
            disabled={isLoading}
          >
            {isLoading ? 'Sending...' : 'Send Reset Link'}
          </button>
        </form>

        <div className={styles.authFooter}>
          Remember your password?
          <Link to="/login" className={styles.authLink}>
            Log in
          </Link>
        </div>
      </div>
    </div>
  );
}
