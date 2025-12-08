import { useState } from 'react';
import { X, MessageSquare, DollarSign } from 'lucide-react';
import styles from './RevisionModal.module.css';

interface RevisionModalProps {
  currentBudget: number;
  onSubmit: (feedback: string, newBudget?: number) => void;
  onCancel: () => void;
}

export const RevisionModal = ({ currentBudget, onSubmit, onCancel }: RevisionModalProps) => {
  const [feedback, setFeedback] = useState('');
  const [adjustBudget, setAdjustBudget] = useState(false);
  const [newBudget, setNewBudget] = useState(currentBudget);

  const handleSubmit = () => {
    if (!feedback.trim()) {
      alert('Please provide feedback for the AI');
      return;
    }
    onSubmit(feedback, adjustBudget ? newBudget : undefined);
  };

  return (
    <div className={styles.overlay} onClick={onCancel}>
      <div className={styles.modal} onClick={e => e.stopPropagation()}>
        <div className={styles.header}>
          <h3>Request Revision</h3>
          <button className={styles.closeBtn} onClick={onCancel}>
            <X size={18} />
          </button>
        </div>

        <div className={styles.body}>
          <div className={styles.field}>
            <label>
              <MessageSquare size={14} /> What would you like changed?
            </label>
            <textarea
              className={styles.textarea}
              placeholder="e.g., Add more outdoor activities, find cheaper hotels, include a day trip to..."
              value={feedback}
              onChange={e => setFeedback(e.target.value)}
              rows={4}
            />
          </div>

          <div className={styles.budgetSection}>
            <label className={styles.checkboxLabel}>
              <input
                type="checkbox"
                checked={adjustBudget}
                onChange={e => setAdjustBudget(e.target.checked)}
              />
              <DollarSign size={14} /> Increase budget
            </label>

            {adjustBudget && (
              <div className={styles.budgetInput}>
                <span className={styles.currency}>$</span>
                <input
                  type="number"
                  value={newBudget}
                  onChange={e => setNewBudget(Number(e.target.value))}
                  min={currentBudget}
                  step={100}
                />
                <span className={styles.currentBudget}>
                  (was ${currentBudget})
                </span>
              </div>
            )}
          </div>
        </div>

        <div className={styles.footer}>
          <button className={styles.cancelBtn} onClick={onCancel}>
            Cancel
          </button>
          <button className={styles.submitBtn} onClick={handleSubmit}>
            Submit Revision Request
          </button>
        </div>
      </div>
    </div>
  );
};

