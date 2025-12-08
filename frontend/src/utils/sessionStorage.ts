// Utility to persist active trip generation session across navigation

import type { TripPreferences } from '../types';

const STORAGE_KEY = 'coastline_active_session';

export interface ActiveSession {
  sessionId: string;
  preferences: TripPreferences;
  startedAt: number; // Unix timestamp
  status: 'generating' | 'awaiting_approval' | 'finalizing';
  tripTitle?: string; // Extracted from preferences for display
}

export const sessionStorage = {
  save: (session: ActiveSession): void => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
    } catch (e) {
      console.error('Failed to save session to localStorage:', e);
    }
  },

  get: (): ActiveSession | null => {
    try {
      const data = localStorage.getItem(STORAGE_KEY);
      if (!data) return null;
      
      const session = JSON.parse(data) as ActiveSession;
      
      // Check if session is too old (> 30 minutes)
      const MAX_AGE_MS = 30 * 60 * 1000;
      if (Date.now() - session.startedAt > MAX_AGE_MS) {
        sessionStorage.clear();
        return null;
      }
      
      return session;
    } catch (e) {
      console.error('Failed to read session from localStorage:', e);
      return null;
    }
  },

  update: (partial: Partial<ActiveSession>): void => {
    const current = sessionStorage.get();
    if (current) {
      sessionStorage.save({ ...current, ...partial });
    }
  },

  clear: (): void => {
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch (e) {
      console.error('Failed to clear session from localStorage:', e);
    }
  },

  // Get human-readable elapsed time
  getElapsedTime: (startedAt: number): string => {
    const seconds = Math.floor((Date.now() - startedAt) / 1000);
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds}s`;
  }
};

