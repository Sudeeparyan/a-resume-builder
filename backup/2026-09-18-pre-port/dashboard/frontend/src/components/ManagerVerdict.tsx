/**
 * What the hiring manager wants -- written without ever seeing her profile.
 *
 * That is the whole point, so the panel says so plainly. A verdict she thinks
 * was tailored to her would be read as encouragement; this one is a bar.
 */
import { useEffect, useRef, useState } from "react";
import { api, subscribeRun, type ManagerVerdict as Verdict } from "../lib/api";
import { Section } from "./ui";

export default function ManagerVerdictPanel({ jobId }: { jobId: string }) {
  const [verdict, setVerdict] = useState<Verdict | null>(null);
  const [degraded, setDegraded] = useState(false);
  const [stale, setStale] = useState(false);
  const [running, setRunning] = useState(false);
  const [note, setNote] = useState("");
  const [err, setErr] = useState("");
  const stop = useRef<(() => void) | null>(null);

  // A different job means a different bar. Drop everything on the floor.
  useEffect(() => {
    setVerdict(null);
    setDegraded(false);
    setStale(false);
    setErr("");
    setNote("");
    setRunning(false);
    api
      .manager(jobId)
      .then((r) => {
        setVerdict(r.verdict);
        setDegraded(r.degraded);
        setStale(!!r.stale);
      })
      .catch(() => {
        /* 404 just means it has not been asked yet */
      });
    return () => stop.current?.();
  }, [jobId]);

  const run = async (force = false) => {
    setErr("");
    setRunning(true);
    setNote("Reading the ad the way the hiring manager would…");
    try {
      const res = await api.managerRun(jobId, force);
      if (res.cached && res.verdict) {
        setVerdict(res.verdict);
        setDegraded(!!res.degraded);
        setRunning(false);
        return;
      }
      if (!res.run_id) throw new Error("The run did not start.");
      stop.current = subscribeRun(res.run_id, async (ev) => {
        if (ev.message) setNote(ev.message);
        if (ev.type === "run_finished") {
          try {
            const r = await api.manager(jobId);
            setVerdict(r.verdict);
            setDegraded(r.degraded);
            setStale(false);
          } catch (e: any) {
            setErr(e.message);
          }
          setRunning(false);
        }
        if (ev.type === "error") {
          setErr(ev.message || "That did not finish.");
          setRunning(false);
        }
      });
    } catch (e: any) {
      setErr(e.message);
      setRunning(false);
    }
  };

  if (!verdict && !running) {
    return (
      <Section title="What the hiring manager wants">
        {err && <div className="banner bad">{err}</div>}
        <p className="small muted" style={{ marginTop: 0 }}>
          An outside read on this job — what disqualifies a candidate, what makes
          them sit up, and the projects worth building before you apply. It is
          written <strong>without</strong> looking at your profile, so it is a bar
          rather than a compliment.
        </p>
        <button className="primary small" onClick={() => run(false)}>
          Ask the hiring manager
        </button>
      </Section>
    );
  }

  if (running) {
    return (
      <Section title="What the hiring manager wants">
        <div style={{ display: "flex", alignItems: "center", gap: 9 }}>
          <span className="spin" />
          <span className="small muted">{note || "Working…"}</span>
        </div>
        <div className="skeleton" style={{ height: 10, marginTop: 12 }} />
        <div className="skeleton" style={{ height: 10, marginTop: 6, width: "82%" }} />
        <div className="skeleton" style={{ height: 10, marginTop: 6, width: "63%" }} />
      </Section>
    );
  }

  const v = verdict!;
  return (
    <Section title="What the hiring manager wants">
      <div style={{ display: "flex", gap: 7, flexWrap: "wrap", marginBottom: 10 }}>
        <span className="pill" title="This verdict never saw your profile">
          written blind
        </span>
        {degraded && <span className="pill warn">from the ad only</span>}
        {stale && <span className="pill warn">the ad has changed</span>}
        <div className="spacer" />
        <button className="ghost small" onClick={() => run(true)}>
          Ask again
        </button>
      </div>

      {err && <div className="banner bad">{err}</div>}
      {degraded && v.degraded_note && (
        <div className="banner warn small">{v.degraded_note}</div>
      )}

      {v.role_in_one_line && <p style={{ marginTop: 0 }}>{v.role_in_one_line}</p>}
      {v.what_breaks_without_this_hire && (
        <p className="small dim">{v.what_breaks_without_this_hire}</p>
      )}

      {v.the_bar && (
        <div className="banner info" style={{ marginTop: 10 }}>
          <strong>The bar.</strong> {v.the_bar}
        </div>
      )}

      {!!v.mandatory?.length && (
        <>
          <h3>Miss one of these and you do not get a call</h3>
          {v.mandatory.map((m, i) => (
            <div className="verdict-block mandatory" key={i}>
              <div className="lead">{m.requirement}</div>
              {m.why_disqualifying && <div className="small dim">{m.why_disqualifying}</div>}
              {m.how_i_check && (
                <div className="small muted" style={{ marginTop: 3 }}>
                  How they check: {m.how_i_check}
                </div>
              )}
              {m.evidence_quote && <div className="quote small">“{m.evidence_quote}”</div>}
            </div>
          ))}
        </>
      )}

      {!!v.perfect_projects?.length && (
        <>
          <h3>Build one of these and they say yes</h3>
          {v.perfect_projects.map((p, i) => (
            <div className="verdict-block project" key={i}>
              <div className="lead">{p.name}</div>
              {p.what_it_proves && <div className="small">{p.what_it_proves}</div>}
              {!!p.stack?.length && (
                <div className="chipwrap" style={{ marginTop: 6 }}>
                  {p.stack.map((s) => (
                    <span className="chip mono" key={s}>
                      {s}
                    </span>
                  ))}
                </div>
              )}
              {p.scope && (
                <div className="small muted" style={{ marginTop: 5 }}>
                  {p.scope}
                  {p.rough_effort_days ? ` · about ${p.rough_effort_days} days` : ""}
                </div>
              )}
              {p.what_bad_looks_like && (
                <div className="small muted" style={{ marginTop: 5 }}>
                  <strong>Not this:</strong> {p.what_bad_looks_like}
                </div>
              )}
            </div>
          ))}
          <div className="small muted">
            These are things to <em>build</em>, not things to claim. Nothing here goes
            on a resume until you have actually made it and recorded it in Profile.
          </div>
        </>
      )}

      {!!v.strong_signals?.length && (
        <>
          <h3>What makes them sit up</h3>
          {v.strong_signals.map((s, i) => (
            <div className="verdict-block signal" key={i}>
              <div className="lead">
                {s.signal}{" "}
                {s.how_rare && <span className="chip">{s.how_rare}</span>}
              </div>
              {s.why_it_moves_me && <div className="small dim">{s.why_it_moves_me}</div>}
            </div>
          ))}
        </>
      )}

      {!!v.screening_questions?.length && (
        <>
          <h3>What they would ask</h3>
          {v.screening_questions.map((q, i) => (
            <div className="verdict-block" key={i}>
              <div className="lead">{q.question}</div>
              {q.what_a_good_answer_contains && (
                <div className="small" style={{ color: "var(--good)" }}>
                  Good: {q.what_a_good_answer_contains}
                </div>
              )}
              {q.what_a_bad_answer_sounds_like && (
                <div className="small" style={{ color: "var(--bad)" }}>
                  Bad: {q.what_a_bad_answer_sounds_like}
                </div>
              )}
            </div>
          ))}
        </>
      )}

      {!!v.instant_rejects?.length && (
        <>
          <h3>What closes the tab</h3>
          {v.instant_rejects.map((r, i) => (
            <div className="verdict-block reject" key={i}>
              <div className="lead">{r.signal}</div>
              {r.why && <div className="small dim">{r.why}</div>}
            </div>
          ))}
        </>
      )}

      {!!v.sources?.length && (
        <>
          <h3>Where this came from</h3>
          <ul className="small">
            {v.sources.slice(0, 10).map((s) => (
              <li key={s}>
                <a href={s} target="_blank" rel="noreferrer">
                  {s.replace(/^https?:\/\//, "").slice(0, 70)}
                </a>
              </li>
            ))}
          </ul>
        </>
      )}
    </Section>
  );
}
