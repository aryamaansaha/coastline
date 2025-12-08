import { useEffect, useState } from 'react';
import { X, CheckCircle, AlertCircle, Info } from 'lucide-react';
import styles from './Toast.module.css';

export interface ToastData {
  id: string;
  message: string;
  type: 'success' | 'error' | 'info';
  action?: {
    label: string;
    onClick: () => void;
  };
  duration?: number; // ms, 0 = no auto-dismiss
}

interface ToastProps {
  toast: ToastData;
  onDismiss: (id: string) => void;
}

const Toast = ({ toast, onDismiss }: ToastProps) => {
  const [isExiting, setIsExiting] = useState(false);

  useEffect(() => {
    if (toast.duration !== 0) {
      const timer = setTimeout(() => {
        setIsExiting(true);
        setTimeout(() => onDismiss(toast.id), 300);
      }, toast.duration || 5000);
      return () => clearTimeout(timer);
    }
  }, [toast, onDismiss]);

  const handleDismiss = () => {
    setIsExiting(true);
    setTimeout(() => onDismiss(toast.id), 300);
  };

  const Icon = toast.type === 'success' ? CheckCircle 
             : toast.type === 'error' ? AlertCircle 
             : Info;

  return (
    <div className={`${styles.toast} ${styles[toast.type]} ${isExiting ? styles.exiting : ''}`}>
      <Icon size={20} className={styles.icon} />
      <span className={styles.message}>{toast.message}</span>
      {toast.action && (
        <button className={styles.actionBtn} onClick={toast.action.onClick}>
          {toast.action.label}
        </button>
      )}
      <button className={styles.closeBtn} onClick={handleDismiss}>
        <X size={16} />
      </button>
    </div>
  );
};

// Toast Container - place this at root level
interface ToastContainerProps {
  toasts: ToastData[];
  onDismiss: (id: string) => void;
}

export const ToastContainer = ({ toasts, onDismiss }: ToastContainerProps) => {
  if (toasts.length === 0) return null;
  
  return (
    <div className={styles.container}>
      {toasts.map(toast => (
        <Toast key={toast.id} toast={toast} onDismiss={onDismiss} />
      ))}
    </div>
  );
};

// Hook to manage toasts
export const createToastManager = () => {
  let toasts: ToastData[] = [];
  let listeners: Array<(toasts: ToastData[]) => void> = [];

  const notify = () => {
    listeners.forEach(listener => listener([...toasts]));
  };

  return {
    subscribe: (listener: (toasts: ToastData[]) => void) => {
      listeners.push(listener);
      listener([...toasts]);
      return () => {
        listeners = listeners.filter(l => l !== listener);
      };
    },
    
    show: (toast: Omit<ToastData, 'id'>) => {
      const id = `toast-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
      toasts = [...toasts, { ...toast, id }];
      notify();
      return id;
    },
    
    dismiss: (id: string) => {
      toasts = toasts.filter(t => t.id !== id);
      notify();
    },
    
    clear: () => {
      toasts = [];
      notify();
    }
  };
};

// Global toast manager instance
export const toastManager = createToastManager();

