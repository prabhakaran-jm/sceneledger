/* Tiny shared presentational primitives — no state, no logic. */

type IconName = "check" | "warning" | "cross" | "info" | "shield";

const ICON_PATHS: Record<IconName, string> = {
  check: "M4 10.5l4 4 8-9",
  warning: "M10 3L2 17h16L10 3zm0 5v4m0 3v.5",
  cross: "M5 5l10 10M15 5L5 15",
  info: "M10 6v.5M10 9v5m-7-4a7 7 0 1114 0 7 7 0 01-14 0z",
  shield: "M10 2l6 2.5V9c0 4-2.5 6.7-6 8-3.5-1.3-6-4-6-8V4.5L10 2z",
};

export function Icon({
  name,
  size = 16,
}: {
  name: IconName;
  size?: number;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={ICON_PATHS[name]} />
    </svg>
  );
}

const STATUS_ICON: Record<string, IconName> = {
  verified: "check",
  current: "check",
  complete: "check",
  warning: "warning",
  stale: "warning",
  blocked: "cross",
};

/** Status badge — always icon + text, never color alone. */
export function StatusBadge({
  status,
  className,
}: {
  status: string;
  className?: string;
}) {
  const icon = STATUS_ICON[status];
  return (
    <span className={className ?? `badge ${status}`}>
      {icon && <Icon name={icon} size={12} />}
      {status}
    </span>
  );
}

export function Spinner() {
  return <span className="spinner" aria-hidden="true" />;
}
