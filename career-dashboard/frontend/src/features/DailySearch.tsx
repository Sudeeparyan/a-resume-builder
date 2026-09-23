import { useEffect, useState } from "react";
import { Search, Settings2, ArrowUpRight } from "lucide-react";
import { api } from "../api";
import { Badge, Field, Modal, Running, Empty } from "../components/UI";
import { JobList } from "../components/JobList";
import type { Summary } from "../types";
export default function DailySearch({
  data,
  refresh,
  notify,
  onJob,
  onAdd,
}: {
  data: Summary;
  refresh: () => Promise<void>;
  notify: (s: string, e?: boolean) => void;
  onJob: (id: string) => void;
  onAdd: () => void;
}) {
  const [g, setG] = useState<any>(null);
  const [runs, setRuns] = useState<any[]>([]);
  const [busy, setBusy] = useState(false);
  const [all, setAll] = useState(false);
  const [preset, setPreset] = useState("default");
  useEffect(() => {
    api("/search-runs")
      .then((r) => setRuns(r.runs))
      .catch((e) => notify(e.message, true));
  }, [data]);
  useEffect(() => {
    api<{ preset: string }>("/v2/discovery/preferences")
      .then((p) => setPreset(p.preset || "default"))
      .catch(() => {});
  }, []);
  const current = runs.find((r) => r.date === data.goals.date);
  const ids = new Set((current?.jobs || []).map((j: any) => j.id));
  const latestDiscovery = data.runs.find((r) => r.kind === "discovery");
  const running = data.runs.find(
    (r) => r.kind === "discovery" && ["queued", "running"].includes(r.state),
  );
  return (
    <>
      <div className="page-title">
        <div>
          <div className="eyebrow">CONSISTENCY OVER PERFECTION</div>
          <h1>Daily Search</h1>
          <p>
            A lasting job list with relevance, freshness and company-evidence gates.
          </p>
        </div>
        <button
          className="secondary"
          onClick={() => setG({ ...data.goals.settings })}
        >
          <Settings2 size={17} />
          Edit target
        </button>
      </div>
      <section className="focus-card">
        <div>
          <Badge tone="lime">{data.goals.date} · US CENTRAL TIME</Badge>
          <h2>{data.goals.remaining_today} left on today’s plan</h2>
          <p>
            {data.goals.daily_base} scheduled + {data.goals.carryover} carried
            forward − {data.goals.ahead} advance credit.
            <br />
            {data.goals.today_completed} confirmed today. Saving a job or
            preparing a resume does not count as applying.
          </p>
          <button
            disabled={busy || !!running}
            onClick={async () => {
              setBusy(true);
              try {
                await api("/v2/agents/run", "POST", { kind: "discovery", preset });
                await refresh();
                notify(
                  "Searching current postings against your active profile.",
                );
              } catch (e) {
                notify((e as Error).message, true);
              } finally {
                setBusy(false);
              }
            }}
          >
            <Search size={17} />
            {running ? "Discovery running…" : "Find suitable jobs"}
          </button>
          <Field label="Search mix">
            <select
              value={preset}
              onChange={(e) => {
                setPreset(e.target.value);
                api("/v2/discovery/preferences", "PUT", {
                  preset: e.target.value,
                }).catch((err) => notify((err as Error).message, true));
              }}
            >
              <option value="default">Default discovery · exactly 5 jobs, ranked by fit · AI web search, US only</option>
              <option value="balanced_five">Balanced five · 2 startup, 1 mid, 2 large (mid/large need tier S, A or B)</option>
              <option value="portals">Tracked career pages · Greenhouse/Lever/Ashby feeds, no AI</option>
            </select>
          </Field>
        </div>
        <div className="progress-dial">
          <strong>
            {data.goals.week_completed}
            <small>/{data.goals.current_week_target}</small>
          </strong>
          <span>this week</span>
        </div>
      </section>
      <section className="card week-card">
        <div className="section-title">
          <h2>Your week</h2>
          <Badge>{data.goals.weekly_target} per full week</Badge>
        </div>
        <div className="week-grid">
          {data.goals.schedule.map((d) => (
            <div key={d.date} className={d.today ? "today" : ""}>
              <span>{d.label}</span>
              <small>{d.date.slice(5)}</small>
              <strong>
                {d.completed}
                <small>/{d.planned}</small>
              </strong>
              <progress max={Math.max(1, d.planned)} value={d.completed} />
            </div>
          ))}
        </div>
        <p className="small">
          Tracking starts {data.goals.settings.start_date}. Partial weeks are
          prorated. Unfinished targets carry across days and weeks. Email
          receipt dates are used only when an explicit submission date is
          unavailable.
        </p>
      </section>
      {latestDiscovery && <Running run={latestDiscovery} />}
      {latestDiscovery?.result?.summary && (
        <details className="search-notes">
          <summary>What the last job search tried, and why it stopped</summary>
          <p className="small">{latestDiscovery.result.summary}</p>
          {!!latestDiscovery.result.excluded?.length && (
            <>
              <p className="small">
                <b>Excluded by the sponsorship gate</b> — never shown as leads. The exact sentence is
                kept so a wrong call can be restored from the Dashboard.
              </p>
              <table className="small">
                <thead>
                  <tr>
                    <th>Company</th>
                    <th>Role</th>
                    <th>The posting says</th>
                  </tr>
                </thead>
                <tbody>
                  {latestDiscovery.result.excluded.map((e: { company: string; title: string; url: string; sentence: string; reason: string }, i: number) => (
                    <tr key={i}>
                      <td>{e.company}</td>
                      <td>{e.title}</td>
                      <td>
                        “{e.sentence}” <span className="muted">({e.reason})</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
          {!!latestDiscovery.result.rejected_leads?.length && (
            <details>
              <summary className="small">Other leads set aside · {latestDiscovery.result.rejected_leads.length}</summary>
              <pre className="small">{latestDiscovery.result.rejected_leads.join("\n")}</pre>
            </details>
          )}
        </details>
      )}
      <section className="card">
        <div className="section-title">
          <div className="segmented">
            <button
              className={!all ? "selected" : ""}
              onClick={() => setAll(false)}
            >
              Today’s finds
            </button>
            <button
              className={all ? "selected" : ""}
              onClick={() => setAll(true)}
            >
              All saved jobs · {data.jobs.length}
            </button>
          </div>
          <button className="text-button" onClick={onAdd}>
            ＋ Save posting
          </button>
        </div>
        <JobList
          jobs={all ? data.jobs : data.jobs.filter((j) => ids.has(j.id))}
          onSelect={onJob}
        />
      </section>
      <section className="card spaced">
        <h2>Search history</h2>
        {runs.length ? (
          runs.map((r) => (
            <details key={r.date}>
              <summary>
                {r.date} · {r.jobs.length} saved postings
              </summary>
              <p className="preserve">
                {r.notes || "No search notes recorded."}
              </p>
              {r.jobs.map((j: any) =>
                j.deleted_at ? (
                  <div className="history-job muted" key={j.id}>
                    {j.company} · {j.title} · removed from active list
                  </div>
                ) : (
                  <button
                    className="history-job"
                    key={j.id}
                    onClick={() => onJob(j.id)}
                  >
                    {j.company} · {j.title}
                    <ArrowUpRight size={16} />
                  </button>
                ),
              )}
            </details>
          ))
        ) : (
          <Empty title="Every search has a history">
            New discoveries are saved here and excluded from future results.
          </Empty>
        )}
      </section>
      {g && (
        <Modal title="Set your application plan" onClose={() => setG(null)}>
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              setBusy(true);
              try {
                await api("/v2/goals", "PUT", g);
                await refresh();
                setG(null);
                notify("Plan saved. Your carryover has been recalculated.");
              } catch (e) {
                notify((e as Error).message, true);
              } finally {
                setBusy(false);
              }
            }}
          >
            <Field label="Applications per week">
              <input
                type="number"
                min="1"
                max="200"
                required
                value={g.weekly_target}
                onChange={(e) =>
                  setG({ ...g, weekly_target: Number(e.target.value) })
                }
              />
            </Field>
            <Field label="Start tracking from">
              <input
                type="date"
                max={data.goals.date}
                required
                value={g.start_date}
                onChange={(e) => setG({ ...g, start_date: e.target.value })}
              />
            </Field>
            <fieldset>
              <legend>Application days</legend>
              <div className="day-choices">
                {["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map(
                  (d, i) => (
                    <label key={d}>
                      <input
                        type="checkbox"
                        checked={g.workdays.includes(i)}
                        onChange={(e) =>
                          setG({
                            ...g,
                            workdays: e.target.checked
                              ? [...g.workdays, i]
                              : g.workdays.filter((n: number) => n !== i),
                          })
                        }
                      />
                      {d}
                    </label>
                  ),
                )}
              </div>
            </fieldset>
            <p className="small">
              Changing this plan recalculates unfinished work from the start
              date. Choose a new start date if you want a fresh target.
            </p>
            <button className="primary" disabled={busy || !g.workdays.length}>
              Save plan
            </button>
          </form>
        </Modal>
      )}
    </>
  );
}
