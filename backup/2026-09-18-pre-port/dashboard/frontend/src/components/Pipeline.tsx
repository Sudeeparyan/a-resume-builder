/**
 * What is out, what went quiet, and what was ruled out.
 *
 * Every exclusion shows the sentence that caused it. A wrong exclusion has to
 * stay visible and correctable -- a job that silently disappears is a job she
 * can never argue with.
 */
import { useEffect, useState } from "react";
import { api, type Excluded } from "../lib/api";
import { Empty, Metric } from "./ui";

const STATUSES = [
  "PREPARED", "APPLIED", "SCREEN", "INTERVIEW", "OFFER",
  "REJECTED", "GHOSTED", "WITHDRAWN", "CLOSED",
];
const OPEN = new Set(["PREPARED", "APPLIED", "SCREEN", "INTERVIEW", "OFFER"]);

function daysSince(iso: string): number | null {
  if (!iso) return null;
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return null;
  return Math.floor((Date.now() - t) / 86_400_000);
}

export default function Pipeline() {
  const [rows, setRows] = useState<any[]>([]);
  const [excluded, setExcluded] = useState<Excluded[]>([]);
  const [rules, setRules] = useState<any>({});
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState("");

  const load = () => {
    api
      .tracker()
      .then((t) => {
        setRows(t.applications || []);
        setRules(t.rules || {});
      })
      .catch((e) => setErr(e.message));
    api.excluded(120).then(setExcluded).catch(() => {});
  };

  useEffect(load, []);

  const change = async (id: string, status: string) => {
    setBusy(id);
    try {
      await api.setStatus(id, status);
      load();
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy("");
    }
  };

  const open = rows.filter((r) => OPEN.has((r.status || "").toUpperCase()));
  const quiet = open.filter((r) => {
    const d = daysSince(r.date_applied || r.last_update);
    return d !== null && d >= (rules.ghost_after_days ?? 21);
  });

  return (
    <div className="col" style={{ padding: 12, overflow: "auto" }}>
      {err && <div className="banner bad">{err}</div>}

      <div className="panel">
        <div className="statrow">
          <Metric value={rows.length} label="applications" />
          <Metric value={open.length} label="still open" tone="good" />
          <Metric
            value={quiet.length}
            label="gone quiet"
            tone={quiet.length ? "warn" : undefined}
            title={`No reply for ${rules.ghost_after_days ?? 21} days or more`}
          />
          <Metric value={excluded.length} label="ruled out" />
        </div>
        {quiet.length > 0 && (
          <div className="banner warn small" style={{ marginTop: 12, marginBottom: 0 }}>
            {quiet.length} application{quiet.length === 1 ? " has" : "s have"} had no
            reply for {rules.ghost_after_days ?? 21} days. They will be marked as gone
            quiet, and those companies open up again after{" "}
            {rules.ghost_cooldown_days ?? 90} days — for a <em>different</em> role.
          </div>
        )}
      </div>

      <div className="panel" style={{ padding: 0, overflow: "hidden" }}>
        <div className="paneheader">
          <strong>Your applications</strong>
          <div className="spacer" />
          <button className="ghost small" onClick={load}>
            Refresh
          </button>
        </div>
        {rows.length === 0 ? (
          <Empty title="Nothing applied to yet">
            Build a resume from a job and it will be tracked here automatically.
          </Empty>
        ) : (
          <div className="overflow-x">
            <table>
              <thead>
                <tr>
                  <th>Company</th>
                  <th>Role</th>
                  <th>Tier</th>
                  <th className="num">Score</th>
                  <th>Quiet</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => {
                  const d = daysSince(r.date_applied || r.last_update);
                  const stale =
                    d !== null && OPEN.has((r.status || "").toUpperCase()) &&
                    d >= (rules.ghost_after_days ?? 21);
                  return (
                    <tr key={r.app_id}>
                      <td>
                        {r.job_url ? (
                          <a href={r.job_url} target="_blank" rel="noreferrer">
                            {r.company}
                          </a>
                        ) : (
                          r.company
                        )}
                      </td>
                      <td>{r.role_title}</td>
                      <td>
                        {r.sponsor_tier && (
                          <span className={`tier ${r.sponsor_tier}`}>{r.sponsor_tier}</span>
                        )}
                      </td>
                      <td className="num">{r.score || "—"}</td>
                      <td className={stale ? "" : "muted"}>
                        {d === null ? "—" : `${d}d`}
                        {stale && (
                          <span className="pill warn" style={{ marginLeft: 6 }}>
                            nudge
                          </span>
                        )}
                      </td>
                      <td>
                        <select
                          value={(r.status || "PREPARED").toUpperCase()}
                          disabled={busy === r.app_id}
                          onChange={(e) => change(r.app_id, e.target.value)}
                          style={{ padding: "4px 7px", fontSize: "var(--fs-1)" }}
                        >
                          {STATUSES.map((s) => (
                            <option key={s} value={s}>
                              {s.toLowerCase()}
                            </option>
                          ))}
                        </select>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="panel" style={{ padding: 0, overflow: "hidden" }}>
        <div className="paneheader">
          <strong>Ruled out</strong>
          <span className="small muted">
            with the exact sentence that did it — tell me if one is wrong
          </span>
        </div>
        {excluded.length === 0 ? (
          <div className="empty small">Nothing has been ruled out yet.</div>
        ) : (
          <div className="overflow-x" style={{ maxHeight: 340, overflowY: "auto" }}>
            <table>
              <thead>
                <tr>
                  <th>Company</th>
                  <th>Role</th>
                  <th>Why</th>
                  <th>Their words</th>
                </tr>
              </thead>
              <tbody>
                {excluded.map((e, i) => (
                  <tr key={i}>
                    <td>{e.company}</td>
                    <td>{e.role_title}</td>
                    <td>{e.why}</td>
                    <td className="muted">
                      {e.triggering_sentence ? `“${e.triggering_sentence}”` : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
