export function LoadingState({
  label,
  className = "",
}: {
  label: string;
  className?: string;
}) {
  return (
    <div role="status" className={`loading-state ${className}`}>
      <p>{label}</p>
      <div className="skeleton-lines" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>
    </div>
  );
}
