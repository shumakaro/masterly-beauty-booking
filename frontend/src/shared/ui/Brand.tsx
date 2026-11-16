import { Link } from "react-router-dom";

export function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <Link
      to="/"
      className="brand"
      aria-label={
        compact
          ? "MASTERLY — на главную"
          : "MASTERLY BEAUTY BOOKING — на главную"
      }
    >
      <svg viewBox="0 0 48 48" aria-hidden="true" className="brand-symbol">
        <path d="M8 35V17c0-7 9-9 13-2l3 6 3-6c4-7 13-5 13 2v18M8 35l10-16 6 11 6-11 10 16" />
        <path d="M18 39h12M24 4v4M21 6h6" />
      </svg>
      {!compact && (
        <span>
          masterly <span className="brand-tagline">BEAUTY BOOKING</span>
        </span>
      )}
    </Link>
  );
}
