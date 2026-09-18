import type { RunState } from "../lib/api";

/** Live progress plus an honest time estimate, narrated in plain language. */
export default function RunProgress({ run }: { run: RunState }) {
  const total = run.stages.length || 1;
  const done = run.stages.filter((s) => s.status === "DONE" || s.status === "SKIPPED").length;
  const pct = Math.round((done / total) * 100);
  const running = run.stages.find((s) => s.status === "RUNNING");
  const finished = ["DONE", "FAILED", "CANCELLED"].includes(run.status);

  return (
    <div style={{ marginTop: 12 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <strong style={{ flex: 1 }}>
          {running ? running.label : finished ? run.message || "Finished" : "Starting…"}
        </strong>
        {!finished && run.eta_human && (
          <span className="pill" title="Estimated from how long these steps have taken before">
            {run.eta_human} left
          </span>
        )}
        {run.status === "WAITING_QUOTA" && (
          <span className="pill warn">paused — usage limit</span>
        )}
        <span className="small muted">{fmt(run.elapsed_seconds)}</span>
      </div>

      <div className="progress"><div style={{ width: `${pct}%` }} /></div>

      {run.status === "WAITING_QUOTA" && run.resume_after && (
        <div className="banner warn">
          {run.message} Nothing found so far has been lost.
        </div>
      )}

      <div className="stagelist">
        {run.stages.map((s) => (
          <div key={s.key} className={`stage ${s.status.toLowerCase()}`}>
            <span className="dot">
              {s.status === "DONE" ? "✓"
                : s.status === "SKIPPED" ? "–"
                : s.status === "RUNNING" ? <span className="spin" />
                : s.status === "FAILED" ? "✕" : "·"}
            </span>
            <span style={{ flex: 1 }}>
              {s.label}
              {s.note && <div className="note">{s.note}</div>}
            </span>
            {s.duration_ms > 0 && (
              <span className="small muted">{(s.duration_ms / 1000).toFixed(1)}s</span>
            )}
          </div>
        ))}
      </div>

      {run.source_report?.length > 0 && (
        <details style={{ marginTop: 8 }}>
          <summary className="small muted" style={{ cursor: "pointer" }}>
            Where these came from
          </summary>
          <table style={{ marginTop: 6 }}>
            <tbody>
              {run.source_report.map((r) => (
                <tr key={r.source}>
                  <td>{r.source}</td>
                  <td className="muted">{r.ok ? `${r.count} found` : r.error || "failed"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </details>
      )}

      {run.cost_usd > 0 && (
        <div className="small muted" style={{ marginTop: 6 }}>
          This run cost about ${run.cost_usd.toFixed(2)} in AI usage.
        </div>
      )}
    </div>
  );
}

function fmt(s: number) {
  if (s < 60) return `${s}s`;
  return `${Math.floor(s / 60)}m ${s % 60}s`;
}
