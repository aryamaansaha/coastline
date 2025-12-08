import { X, AlertTriangle } from 'lucide-react';
import styles from './ConfirmModal.module.css';

interface ConfirmModalProps {
  isOpen: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
  variant?: 'danger' | 'warning' | 'info';
}

export const ConfirmModal = ({
  isOpen,
  title,
  message,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  onConfirm,
  onCancel,
  variant = 'danger',
}: ConfirmModalProps) => {
  if (!isOpen) return null;

  return (
    <div className={styles.overlay} onClick={onCancel}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <div className={styles.iconContainer}>
            <AlertTriangle size={24} className={styles[variant]} />
          </div>
          <h3 className={styles.title}>{title}</h3>
          <button className={styles.closeBtn} onClick={onCancel}>
            <X size={18} />
          </button>
        </div>
        
        <div className={styles.content}>
          <p className={styles.message}>{message}</p>
        </div>
        
        <div className={styles.footer}>
          {cancelLabel && (
            <button className={styles.cancelBtn} onClick={onCancel}>
              {cancelLabel}
            </button>
          )}
          <button className={`${styles.confirmBtn} ${styles[variant]}`} onClick={onConfirm}>
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
};

