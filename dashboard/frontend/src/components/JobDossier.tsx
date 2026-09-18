/**
 * Everything known about one job, as a document rather than a scoreboard.
 *
 * The scan already produces most of this -- what a company builds, where it is
 * heading, the pressures that opened the role -- and the old detail pane threw
 * nearly all of it away. This is the answer to "should I spend an evening on
 * this one?", which is the only question that matters here.
 */
import { useEffect, useState } from "react";
import { api, type Job } from "../lib/api";
import ManagerVerdictPanel from "./ManagerVerdict";
import { Meter, Metric, Section, scoreTone } from "./ui";

const LEVEL_LABEL: Record<string, string> = {
  strong: "you know this well",
  used_it: "you have used it",
  touched_it: "you have touched it",
  none: "new to you",
};

export default function JobDossier({
  job,
  onBuildResume,
}: {
  job: Job;
  onBuildResume: (folder: string) => void;
}) {
  const [full, setFull] = useState<Job>(job);
  const [building, setBuilding] = useState(false);
  const [err, setErr] = useState("");
  const [built, setBuilt] = useState("");

  useEffect(() => {
    setFull(job);
    setErr("");
    setBuilt("");
    // The list endpoint omits the ad text; the detail endpoint carries it.
    api.job(job.id).then(setFull).catch(() => setFull(job));
  }, [job.id]);

  const r = full.research || {};
  const p = full.prediction || {};
  const jd = full.jd || {};
  const odds = Math.round((p.probability ?? 0) * 100);

  const build = async () => {
    setBuilding(true);
    setErr("");
    try {
      const res = await api.tailor(full.id);
      setBuilt(res.folder);
      onBuildResume(res.folder);
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBuilding(false);
    }
  };

  const demand = r.demand_map ?? [];
  const byDest = (d: string) => demand.filter((x) => x.destination === d);

  return (
    <div className="dossier panel" style={{ padding: 0 }}>
      <div className="head">
        <div style={{ display: "flex", alignItems: "center", gap: 9 }}>
          <span className={`tier ${full.tier}`}>{full.tier}</span>
          <strong style={{ fontSize: "var(--fs-5)", letterSpacing: "-.3px" }}>
            {full.company}
          </strong>
          <div className="spacer" />
          {full.url && (
            <a href={full.url} target="_blank" rel="noreferrer">
              <button className="ghost small">Open posting</button>
            </a>
          )}
          <button className="primary small" onClick={build} disabled={building}>
            {building ? <span className="spin" /> : "Build a resume"}
          </button>
        </div>
        <div className="dim" style={{ marginTop: 3 }}>
          {full.role_title}
          {full.location ? ` · ${full.location}` : ""}
        </div>

        <div className="statrow" style={{ marginTop: 13 }}>
          <Metric value={Math.round(full.score)} label="match" tone={scoreTone(full.score)} />
          <Metric
            value={`${odds}%`}
            label="interview odds"
            title={p.rationale || ""}
            tone={odds >= 40 ? "good" : odds >= 18 ? "warn" : "bad"}
          />
          <Metric
            value={`${Math.round((p.must_have_coverage ?? 0) * 100)}%`}
            label="must-haves met"
          />
        </div>

        {built && (
          <div className="banner good small" style={{ marginTop: 11, marginBottom: 0 }}>
            Built into <code>{built}</code> — it is open in Resume Builder.
          </div>
        )}
        {err && (
          <div className="banner bad small" style={{ marginTop: 11, marginBottom: 0 }}>
            {err}
          </div>
        )}
      </div>

      <div className="scroll">
        <Section title="Can they hire you">
          <div className="banner info small" style={{ marginBottom: 8 }}>
            {full.tier_label}
          </div>
          <dl className="kv">
            <dt>Sponsorship</dt>
            <dd>{full.reason_label}</dd>
            {full.h1b_approvals > 0 && (
              <>
                <dt>H-1B record</dt>
                <dd>{full.h1b_approvals.toLocaleString()} approvals on file</dd>
              </>
            )}
            {full.cap_exempt && (
              <>
                <dt>Cap-exempt</dt>
                <dd>Can file any time of year, no lottery</dd>
              </>
            )}
            {full.everify && (
              <>
                <dt>E-Verify</dt>
                <dd>Enrolled — matters for the STEM OPT extension</dd>
              </>
            )}
            <dt>Link</dt>
            <dd>
              {full.link_status === "ACTIVE"
                ? "Checked and live"
                : full.link_status === "UNCHECKED"
                  ? "Not checked yet"
                  : full.link_status}
            </dd>
          </dl>
          {full.triggering_sentence && (
            <div className="quote small">“{full.triggering_sentence}”</div>
          )}
          {!!full.ghost_flags?.length && (
            <div className="banner warn small" style={{ marginTop: 9 }}>
              <strong>Worth a second look:</strong> {full.ghost_flags.join(" · ")}
            </div>
          )}
        </Section>

        {!!jd.must_haves?.length && (
          <Section title="What the ad asks for" hint="In the ad's own words, which is what an ATS matches on.">
            <ul>
              {jd.must_haves.map((m, i) => (
                <li key={i}>
                  {m.text}
                  {m.under_required_heading && (
                    <span className="chip" style={{ marginLeft: 6 }}>
                      required
                    </span>
                  )}
                </li>
              ))}
            </ul>
            {!!jd.nice_to_haves?.length && (
              <>
                <h3>Nice to have</h3>
                <div className="chipwrap">
                  {jd.nice_to_haves.map((n, i) => (
                    <span className="chip" key={i}>
                      {n.keyword || n.text}
                    </span>
                  ))}
                </div>
              </>
            )}
          </Section>
        )}

        {jd.hiring_problem && (
          <Section title="Why this role is open">
            <p style={{ marginTop: 0 }}>{jd.hiring_problem}</p>
          </Section>
        )}

        {(r.what_they_do || r.engineering_reality) && (
          <Section title="What they actually build" hint="Their blog and repos beat their job ad.">
            {r.what_they_do && <p style={{ marginTop: 0 }}>{r.what_they_do}</p>}
            {r.engineering_reality && <p className="dim">{r.engineering_reality}</p>}
            {!!r.current_projects?.length && (
              <>
                <h3>Current projects</h3>
                <ul>
                  {r.current_projects.map((x, i) => (
                    <li key={i}>{x}</li>
                  ))}
                </ul>
              </>
            )}
          </Section>
        )}

        {(!!r.future_direction?.length || !!r.pressures?.length) && (
          <Section title="Where they are heading">
            {!!r.future_direction?.length && (
              <ul>
                {r.future_direction.map((x, i) => (
                  <li key={i}>{x}</li>
                ))}
              </ul>
            )}
            {!!r.pressures?.length && (
              <>
                <h3>Pressure on this team</h3>
                <ul>
                  {r.pressures.map((x, i) => (
                    <li key={i}>{x}</li>
                  ))}
                </ul>
              </>
            )}
          </Section>
        )}

        {(r.day_job_months_1_3 || r.day_job_month_12 || r.team_shape) && (
          <Section title="The job itself">
            <dl className="kv">
              {r.team_shape && (
                <>
                  <dt>The team</dt>
                  <dd>{r.team_shape}</dd>
                </>
              )}
              {r.day_job_months_1_3 && (
                <>
                  <dt>Months 1–3</dt>
                  <dd>{r.day_job_months_1_3}</dd>
                </>
              )}
              {r.day_job_month_12 && (
                <>
                  <dt>By month 12</dt>
                  <dd>{r.day_job_month_12}</dd>
                </>
              )}
            </dl>
          </Section>
        )}

        {!!demand.length && (
          <Section
            title="Skills they want"
            hint="Each one goes to exactly one place. A skill you do not have never reaches the resume."
          >
            {(["resume", "study_plan", "honest_gap"] as const).map((dest) =>
              byDest(dest).length ? (
                <div key={dest} style={{ marginBottom: 11 }}>
                  <span className={`dest ${dest}`}>
                    {dest === "resume"
                      ? "goes on the resume"
                      : dest === "study_plan"
                        ? "learn before the interview"
                        : "an honest gap"}
                  </span>
                  <div className="chipwrap" style={{ marginTop: 7 }}>
                    {byDest(dest).map((d) => (
                      <span
                        className={`chip ${
                          d.candidate_level === "strong"
                            ? "strong"
                            : d.candidate_level === "used_it"
                              ? "used"
                              : d.candidate_level === "touched_it"
                                ? "touched"
                                : "gap"
                        }`}
                        key={d.skill}
                        title={`${LEVEL_LABEL[d.candidate_level] ?? ""}${d.note ? ` — ${d.note}` : ""}`}
                      >
                        {d.skill}
                      </span>
                    ))}
                  </div>
                </div>
              ) : null,
            )}
          </Section>
        )}

        <Section title="Your odds">
          <p style={{ marginTop: 0 }}>{p.rationale || "Not estimated yet."}</p>
          {!!p.she_has?.length && (
            <>
              <h3>You can show</h3>
              <div className="chipwrap">
                {p.she_has.map((s) => (
                  <span className="chip strong" key={s}>
                    {s}
                  </span>
                ))}
              </div>
            </>
          )}
          {!!p.she_lacks?.length && (
            <>
              <h3>You cannot, yet</h3>
              <div className="chipwrap">
                {p.she_lacks.map((s) => (
                  <span className="chip gap" key={s}>
                    {s}
                  </span>
                ))}
              </div>
            </>
          )}
          {!!p.lift_if_learned?.length && (
            <>
              <h3>What would move the number</h3>
              {p.lift_if_learned.map((l) => (
                <div key={l.skill} style={{ marginBottom: 8 }}>
                  <div className="small" style={{ display: "flex", gap: 8 }}>
                    <span style={{ flex: 1 }}>{l.skill}</span>
                    <span className="muted">{l.learn_days}d</span>
                    <span className="score">{Math.round(l.new_probability * 100)}%</span>
                  </div>
                  <Meter value={l.new_probability * 100} tone="good" />
                </div>
              ))}
            </>
          )}
        </Section>

        <ManagerVerdictPanel jobId={full.id} />

        {!!r.questions_to_ask?.length && (
          <Section title="Ask them this">
            <ul>
              {r.questions_to_ask.map((q, i) => (
                <li key={i}>{q}</li>
              ))}
            </ul>
          </Section>
        )}

        {!!r.sources?.length && (
          <Section title="Sources">
            <ul className="small">
              {r.sources.slice(0, 12).map((s) => (
                <li key={s}>
                  <a href={s} target="_blank" rel="noreferrer">
                    {s.replace(/^https?:\/\//, "").slice(0, 70)}
                  </a>
                </li>
              ))}
            </ul>
          </Section>
        )}
      </div>
    </div>
  );
}
