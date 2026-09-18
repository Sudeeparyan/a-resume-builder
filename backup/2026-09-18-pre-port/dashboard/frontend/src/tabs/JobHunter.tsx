/**
 * Find work, then keep track of it.
 *
 * Two views behind one segmented control: Find is the scan and the ranked
 * results, Pipeline is what is already out. Splitting them keeps the tab count
 * at three without hiding the tracker somewhere she will never look.
 */
import { useEffect, useRef, useState } from "react";
import {
  api, subscribeRun, type Health, type Job, type RunState,
} from "../lib/api";
import RunProgress from "../components/RunProgress";
import JobDossier from "../components/JobDossier";
import Pipeline from "../components/Pipeline";
import IngestDialog from "../components/IngestDialog";
import { SearchIcon } from "../components/Icons";
import { Empty, Meter, scoreTone } from "../components/ui";

type View = "find" | "pipeline";

export default function JobHunter({
  health,
  onBuildResume,
}: {
  health: Health | null;
  onBuildResume: (folder: string) => void;
}) {
  const [view, setView] = useState<View>("find");
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selected, setSelected] = useState<Job | null>(null);
  const [run, setRun] = useState<RunState | null>(null);
  const [count, setCount] = useState(10);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [showIngest, setShowIngest] = useState(false);
  const unsub = useRef<null | (() => void)>(null);

  const load = async () => {
    try {
      const j = await api.jobs(60);
      setJobs(j);
      setSelected((cur) => (cur ? j.find((x) => x.id === cur.id) ?? j[0] ?? null : j[0] ?? null));
    } catch (e: any) {
      setErr(e.message);
    }
  };

  useEffect(() => {
    load();
    return () => unsub.current?.();
  }, []);

  const start = async () => {
    setErr("");
    setBusy(true);
    try {
      const started = await api.startRun(count);
      setRun(started);
      unsub.current?.();
      unsub.current = subscribeRun(started.id, async (ev) => {
        if (["stage_started", "stage_finished", "eta", "log", "quota_wait"].includes(ev.type)) {
          try {
            setRun(await api.getRun(started.id));
          } catch {
            /* the run may not be queryable for a moment */
          }
        }
        if (ev.type === "run_finished") {
          setRun(await api.getRun(started.id));
          setBusy(false);
          await load();
        }
        if (ev.type === "error") {
          setErr(ev.message);
          setBusy(false);
        }
      });
    } catch (e: any) {
      setErr(e.message);
      setBusy(false);
    }
  };

  const aiOff = health && !health.llm?.available;

  return (
    <div style={{ display: "flex", flexDirection: "column", width: "100%", overflow: "hidden" }}>
      <div
        className="runbar"
        style={{ padding: "10px 12px 0", flexShrink: 0 }}
      >
        <div className="segmented">
          <button className={view === "find" ? "on" : ""} onClick={() => setView("find")}>
            Find
          </button>
          <button className={view === "pipeline" ? "on" : ""} onClick={() => setView("pipeline")}>
            Pipeline
          </button>
        </div>

        {view === "find" && (
          <>
            <button className="primary" onClick={start} disabled={busy}>
              {busy ? <span className="spin" /> : <SearchIcon size={14} />}
              <span style={{ marginLeft: 7 }}>{busy ? "Searching…" : "Find jobs"}</span>
            </button>
            <select
              value={count}
              onChange={(e) => setCount(Number(e.target.value))}
              disabled={busy}
              style={{ width: 90 }}
            >
              {[5, 10, 15, 20, 25].map((n) => (
                <option key={n} value={n}>
                  {n} jobs
                </option>
              ))}
            </select>
            <button onClick={() => setShowIngest(true)} title="Paste an answer from Claude or ChatGPT">
              Paste from Claude
            </button>
          </>
        )}
        <div className="spacer" />
        {jobs.length > 0 && view === "find" && (
          <span className="small muted">{jobs.length} shown, best first</span>
        )}
      </div>

      {view === "pipeline" ? (
        <Pipeline />
      ) : (
        <div className={`deck ${selected ? "" : "single"}`}>
          <div className="col">
            {err && <div className="banner bad">{err}</div>}
            {aiOff && (
              <div className="banner warn small">
                {health?.llm?.degraded_note ||
                  "Running without an AI model. Finding, screening and scoring still work."}
              </div>
            )}
            {run && <RunProgress run={run} />}

            <div className="scroll" style={{ paddingRight: 2 }}>
              {jobs.length === 0 && !busy ? (
                <Empty icon={<SearchIcon size={30} />} title="No jobs yet">
                  Press <strong>Find jobs</strong> to search, or paste an answer from a
                  Claude or ChatGPT project.
                </Empty>
              ) : (
                jobs.map((j) => (
                  <div
                    key={j.id}
                    className={`jobcard ${selected?.id === j.id ? "selected" : ""}`}
                    onClick={() => setSelected(j)}
                  >
                    <div className={`rail ${j.tier}`} />
                    <div className="main">
                      <div className="row1">
                        <span className={`tier ${j.tier}`}>{j.tier}</span>
                        <span className="title">{j.company}</span>
                        <span className="score">{Math.round(j.score)}</span>
                      </div>
                      <div className="row2">
                        <span>{j.role_title}</span>
                        {j.location && <span>· {j.location}</span>}
                        {j.link_status === "ACTIVE" && <span className="pill good">link ok</span>}
                        {!!j.ghost_flags?.length && (
                          <span className="pill warn" title={j.ghost_flags.join(" · ")}>
                            check this
                          </span>
                        )}
                      </div>
                      <div className="row3">
                        <Meter value={j.score} tone={scoreTone(j.score)} />
                        <span className="small muted">
                          {Math.round((j.prediction?.probability ?? 0) * 100)}% odds
                        </span>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {selected && (
            <div className="col">
              <JobDossier job={selected} onBuildResume={onBuildResume} />
            </div>
          )}
        </div>
      )}

      {showIngest && (
        <IngestDialog
          onClose={() => setShowIngest(false)}
          onSaved={() => {
            load();
          }}
        />
      )}
    </div>
  );
}
