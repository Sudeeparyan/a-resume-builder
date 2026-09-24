import { useCallback, useEffect, useRef, useState } from "react";
import { Settings2, ArrowUpRight } from "lucide-react";
import { api } from "../api";
import { useMarket } from "../profiles";
import { AskAssistant, Badge, Field, Modal, Running, Empty } from "../components/UI";
import { JobList } from "../components/JobList";
import { PipelineBuilder, PipelineProgress } from "./SearchPipeline";
import type { PipelineChoice, PipelineInfo, PipelineRun, PipelineStatus, Summary } from "../types";
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
  const market = useMarket();
  const [g, setG] = useState<any>(null);
  const [runs, setRuns] = useState<any[]>([]);
  const [busy, setBusy] = useState(false);
  const [all, setAll] = useState(false);
  const [info, setInfo] = useState<PipelineInfo | null>(null);
  const [choice, setChoice] = useState<PipelineChoice | null>(null);
  const [starting, setStarting] = useState(false);
  useEffect(() => {
    api("/search-runs")
      .then((r) => setRuns(r.runs))
      .catch((e) => notify(e.message, true));
  }, [data]);
  const loadPipeline = useCallback(
    () =>
      api<PipelineInfo>("/v2/pipeline")
        .then((loaded) => {
          setInfo(loaded);
          setChoice((was) => was ?? loaded.preferences);
        })
        .catch((e) => notify((e as Error).message, true)),
    [notify],
  );
  const refreshStatus = useCallback(
    () =>
      api<PipelineStatus>("/v2/pipeline/status", "GET", undefined, { timeout: 15000 })
        .then((status) => setInfo((was) => (was ? { ...was, ...status } : was)))
        .catch(() => {}),
    [],
  );
  useEffect(() => {
    loadPipeline();
  }, [loadPipeline]);
  useEffect(() => {
    refreshStatus();
  }, [data, refreshStatus]);
  const active = !!info?.current;
  useEffect(() => {
    if (active) return;
    const timer = setInterval(refreshStatus, 15000);
    return () => clearInterval(timer);
  }, [active, refreshStatus]);
  useEffect(() => {
    if (!active) return;
    const timer = setInterval(refreshStatus, 3000);
    return () => clearInterval(timer);
  }, [active, refreshStatus]);
  // When a search ends: reload the job list and the estimates it just taught.
  const wasActive = useRef(false);
  useEffect(() => {
    if (wasActive.current && !active) {
      refresh().catch(() => {});
      loadPipeline();
    }
    wasActive.current = active;
  }, [active, refresh, loadPipeline]);
  // Remember her choices (not on the first load), a moment after she stops changing them.
  const firstChoice = useRef(true);
  useEffect(() => {
    if (!choice?.provider) return;
    if (firstChoice.current) {
      firstChoice.current = false;
      return;
    }
    const timer = setTimeout(
      () => api("/v2/pipeline/preferences", "PUT", choice).catch((e) => notify((e as Error).message, true)),
      600,
    );
    return () => clearTimeout(timer);
  }, [choice, notify]);
  const start = async () => {
    if (!choice) return;
    setStarting(true);
    try {
      const run = await api<PipelineRun>("/v2/pipeline/run", "POST", choice);
      setInfo((was) => (was ? { ...was, current: run } : was));
      notify("Search started. It keeps running if you leave this page.");
      await refresh();
    } catch (e) {
      notify((e as Error).message, true);
    } finally {
      setStarting(false);
    }
  };
  const stop = async (run: PipelineRun) => {
    try {
      const stopped = await api<PipelineRun>(`/v2/pipeline/${run.id}/stop`, "POST");
      setInfo((was) => (was ? { ...was, current: stopped } : was));
      notify("Stopping after the current step. Finished work is kept.");
    } catch (e) {
      notify((e as Error).message, true);
    }
  };
  const raiseBudget = async (limit: number) => {
    try {
      await api("/v2/agent-control/budget", "PUT", { daily_call_limit: limit });
      await refreshStatus();
      notify(`Your daily AI-call limit is now ${limit}.`);
    } catch (e) {
      notify((e as Error).message, true);
    }
  };
  const current = runs.find((r) => r.date === data.goals.date);
  const ids = new Set((current?.jobs || []).map((j: any) => j.id));
  const latestDiscovery = data.runs.find((r) => r.kind === "discovery");
  const running = data.runs.find(
    (r) => r.kind === "discovery" && ["queued", "running"].includes(r.state),
  );
  const builder =
    info && choice ? (
      <PipelineBuilder
        info={info}
        choice={choice}
        onChoice={setChoice}
        running={active}
        starting={starting}
        onStart={start}
        onEditPlan={() => setG({ ...data.goals.settings })}
        onRaiseBudget={raiseBudget}
      />
    ) : (
      <section className="card" role="status" aria-label="Loading search options">
        <div className="skeleton skeleton-title" />
        <div className="skeleton skeleton-card" />
      </section>
    );
  const shown = info?.current ?? info?.last;
  const progress = info && shown && (
    <PipelineProgress run={shown} info={info} onStop={() => stop(shown)} onJob={onJob} />
  );
  return (
    <>
      <div className="page-title">
        <div>
          <div className="eyebrow">CONSISTENCY OVER PERFECTION</div>
          <h1>Daily Search</h1>
          <p>
            Choose how many jobs you want and which helpers should run. You will
            see how long it takes before you start.
          </p>
        </div>
        <div className="actions">
          <AskAssistant
            prompts={[
              { label: "How is the search going?", text: "How is the Daily Search going right now?" },
              { label: "Why were jobs turned away?", text: "Why did the last search save only the jobs it did? Show me what it turned away and why." },
              { label: "Run a search from the chat", text: "Run the daily search for 2 jobs with research, a tailored resume, the study plan and the PDF", send: false },
            ]}
          />
          <button
            className="secondary"
            onClick={() => setG({ ...data.goals.settings })}
          >
            <Settings2 size={17} />
            Edit plan
          </button>
        </div>
      </div>
      <section className="focus-card">
        <div>
          <Badge tone="lime">{data.goals.date} · {market.time.toUpperCase()}</Badge>
          <h2>{data.goals.remaining_today} left on today’s plan</h2>
          <p>
            {data.goals.daily_base} scheduled + {data.goals.carryover} carried
            forward − {data.goals.ahead} advance credit.
            <br />
            {data.goals.today_completed} confirmed today. Saving a job or
            preparing a resume does not count as applying.
          </p>
        </div>
        <div className="progress-dial">
          <strong>
            {data.goals.week_completed}
            <small>/{data.goals.current_week_target}</small>
          </strong>
          <span>this week</span>
        </div>
      </section>
      {active ? (
        <>
          {progress}
          {builder}
        </>
      ) : (
        <>
          {builder}
          {progress}
        </>
      )}
      {running && !active && <Running run={running} />}
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
