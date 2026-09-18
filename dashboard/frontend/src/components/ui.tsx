/**
 * The small shared pieces, so the three tabs stop hand-rolling inline styles.
 */
import type { ReactNode } from "react";

export function Metric({
  value,
  label,
  tone,
  title,
}: {
  value: ReactNode;
  label: string;
  tone?: "good" | "warn" | "bad";
  title?: string;
}) {
  return (
    <div className={`metric ${tone ?? ""}`} title={title}>
      <div className="metric-value">{value}</div>
      <div className="metric-label">{label}</div>
    </div>
  );
}

/** 0–100. Anything outside that is clamped rather than overflowing the bar. */
export function Meter({
  value,
  tone,
  title,
}: {
  value: number;
  tone?: "good" | "warn" | "bad";
  title?: string;
}) {
  const pct = Math.max(0, Math.min(100, Number.isFinite(value) ? value : 0));
  return (
    <div className={`meter ${tone ?? ""}`} title={title}>
      <span style={{ width: `${pct}%` }} />
    </div>
  );
}

export function Chip({
  children,
  kind,
  mono,
  title,
}: {
  children: ReactNode;
  kind?: "strong" | "used" | "touched" | "gap";
  mono?: boolean;
  title?: string;
}) {
  return (
    <span className={`chip ${kind ?? ""} ${mono ? "mono" : ""}`} title={title}>
      {children}
    </span>
  );
}

export function Section({
  title,
  children,
  hint,
}: {
  title: string;
  children: ReactNode;
  hint?: string;
}) {
  return (
    <div className="section">
      <h3>{title}</h3>
      {hint && (
        <div className="small muted" style={{ marginTop: -4, marginBottom: 7 }}>
          {hint}
        </div>
      )}
      {children}
    </div>
  );
}

export function Empty({
  icon,
  title,
  children,
}: {
  icon?: ReactNode;
  title: string;
  children?: ReactNode;
}) {
  return (
    <div className="empty-hero">
      {icon && <div className="empty-hero-icon">{icon}</div>}
      <div className="empty-hero-title">{title}</div>
      {children && (
        <p className="small muted" style={{ maxWidth: 340, margin: "6px auto 0" }}>
          {children}
        </p>
      )}
    </div>
  );
}

/** Score colour follows the decision thresholds in system/modes/_shared.md. */
export function scoreTone(score: number): "good" | "warn" | "bad" {
  if (score >= 80) return "good";
  if (score >= 55) return "warn";
  return "bad";
}
