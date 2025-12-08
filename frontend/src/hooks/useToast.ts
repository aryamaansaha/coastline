import { useState, useEffect } from 'react';
import { toastManager, type ToastData } from '../components/Toast';

export const useToast = () => {
  const [toasts, setToasts] = useState<ToastData[]>([]);

  useEffect(() => {
    return toastManager.subscribe(setToasts);
  }, []);

  return {
    toasts,
    show: toastManager.show,
    dismiss: toastManager.dismiss,
    clear: toastManager.clear
  };
};

// Convenience functions for direct use (outside React components)
export const toast = {
  success: (message: string, action?: ToastData['action']) => 
    toastManager.show({ message, type: 'success', action }),
  error: (message: string, action?: ToastData['action']) => 
    toastManager.show({ message, type: 'error', action }),
  info: (message: string, action?: ToastData['action']) => 
    toastManager.show({ message, type: 'info', action }),
};

