import { APP_NAME } from '../brand';

export const Logo = ({ className = 'h-8 w-8' }) => (
  <svg viewBox="0 0 64 64" className={className} role="img" aria-label={APP_NAME}>
    <rect width="64" height="64" rx="14" fill="#1d4ed8" />
    <circle cx="25" cy="32" r="12" fill="none" stroke="#ffffff" strokeWidth="5" />
    <circle cx="39" cy="32" r="12" fill="none" stroke="#5eead4" strokeWidth="5" />
  </svg>
);
