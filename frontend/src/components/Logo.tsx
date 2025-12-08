import logoBlack from '../assets/logo_black.png';
import styles from './Logo.module.css';

interface LogoProps {
  size?: 'sm' | 'md' | 'lg';
  showText?: boolean;
  className?: string;
}

export const Logo = ({ size = 'md', showText = true, className = '' }: LogoProps) => {
  const sizeClass = styles[size];
  
  return (
    <div className={`${styles.logo} ${sizeClass} ${className}`}>
      <img src={logoBlack} alt="Coastline" className={styles.icon} />
      {showText && <span className={styles.text}>Coastline</span>}
    </div>
  );
};

