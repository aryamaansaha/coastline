import styles from './BudgetBar.module.css';

interface BudgetBarProps {
  totalCost: number;
  budgetLimit: number;
  showLabels?: boolean;
}

export const BudgetBar = ({ totalCost, budgetLimit, showLabels = true }: BudgetBarProps) => {
  const percent = Math.min((totalCost / budgetLimit) * 100, 100);
  const isOver = totalCost > budgetLimit;
  
  return (
    <div className={styles.container}>
      {showLabels && (
        <div className={styles.labels}>
          <span className={isOver ? styles.overBudget : ''}>
            Total: ${totalCost.toFixed(0)}
          </span>
          <span>Budget: ${budgetLimit.toFixed(0)}</span>
        </div>
      )}
      <div className={styles.track}>
        <div 
          className={`${styles.fill} ${isOver ? styles.over : styles.under}`}
          style={{ width: `${percent}%` }}
        />
      </div>
      {isOver && (
        <div className={styles.warning}>
          ⚠️ ${(totalCost - budgetLimit).toFixed(0)} over budget
        </div>
      )}
    </div>
  );
};

