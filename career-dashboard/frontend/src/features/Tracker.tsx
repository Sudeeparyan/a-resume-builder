import { useEffect, useState } from "react";
import { ArrowUpRight, Building2, Download, Radar, Search, ShieldCheck, ShieldX } from "lucide-react";
import { api, safeUrl } from "../api";
import { Badge, Empty, Loading } from "../components/UI";
import { statusLabel } from "../components/JobList";

/** One row of the Sponsorship Tracker (backend/services/market_tracker.py). */
export type TrackerRow = {
  key: string;
  company: string;
  title: string;
  location: string;
  url: string;
  source_label: string;
  posted_at: string;
  statement: string;
  statement_label: string;
  sentence: string;
  tier: string;
  cap_exempt: number;
  everify: number;
  h1b_approvals: number;
  h1b_denials: number;
  h1b_years: string;
  h1b_name: string;
  pay_min: number | null;
  pay_max: number | null;
  pay_text: string;
  fit_score: number | null;
  outcome: string;
  outcome_label: string;
  outcome_reason: string;
  mine: string;
  first_seen: string;
  last_seen: string;
};

type TrackerData = {
  items: TrackerRow[];
  total: number;
  page: number;
  page_size: number;
  summary: {
    postings: number;
    employers: number;
    with_h1b_record: number;
    says_sponsors: number;
    refusing: number;
    last_read: string;
  };
  sponsor_boards: { boards: number; verified_on?: string; read_ever?: number; last_read?: string; error?: string };
};

const START = {
  q: "",
  tier: "",
  statement: "",
  source: "",
  outcome: "",
  h1b: "",
  min_pay: "",
  seen_within: "",
  hide_refusing: "1",
  show_applied: "",
  sort: "best",
};
type Filters = typeof START;

const TIER_TEXT: Record<string, string> = {
  S: "S · cap-exempt",
  A: "A · says it sponsors",
  B: "B · proven H-1B sponsor",
  C: "C · silent, no record",
  EXCLUDED: "Excluded",
};
const tierTone = (tier: string) =>
  tier === "S" || tier === "A" ? "green" : tier === "B" ? "lime" : tier === "EXCLUDED" ? "red" : "neutral";
const statementTone = (s: string) => (s === "supports" ? "green" : s === "silent" ? "neutral" : "red");
const money = (n: number) => "$" + Math.round(n / 1000) + "k";
const day = (iso: string) => (iso ? iso.slice(0, 10) : "");

export function query(filters: Filters, page = 1) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => v && params.set(k, v));
  if (page > 1) params.set("page", String(page));
  return params.toString();
}

export default function Tracker({
  notify,
  refresh,
}: {
  notify: (s: string, e?: boolean) => void;
  refresh: () => Promise<void>;
}) {
  const [filters, setFilters] = useState<Filters>(START);
  const [typed, setTyped] = useState("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<TrackerData>();
  const [saving, setSaving] = useState("");
  // Typing waits a moment before searching, so each keystroke is not a request.
  useEffect(() => {
    const timer = setTimeout(() => setFilters((f) => (f.q === typed ? f : { ...f, q: typed })), 300);
    return () => clearTimeout(timer);
  }, [typed]);
  useEffect(() => setPage(1), [filters]);
  const load = () =>
    api<TrackerData>("/v2/tracker?" + query(filters, page))
      .then(setData)
      .catch((e) => notify(e.message, true));
  useEffect(() => {
    load();
  }, [filters, page]);
  const set = (k: keyof Filters) => (e: { target: { value: string } }) =>
    setFilters({ ...filters, [k]: e.target.value });
  async function save(row: TrackerRow) {
    setSaving(row.key);
    try {
      const result = await api("/v2/tracker/save", "POST", { key: row.key });
      if (result.excluded) notify(`Not saved: the posting says "${result.sentence}"`, true);
      else if (result.blocked) notify("Not saved: " + result.note, true);
      else notify(result.duplicate ? "Already in your jobs." : `${row.company} · ${row.title} saved to your jobs.`);
      await Promise.all([load(), refresh()]);
    } catch (e) {
      notify((e as Error).message, true);
    } finally {
      setSaving("");
    }
  }
  if (!data) return <Loading label="Loading the Sponsorship Tracker" />;
  const s = data.summary;
  const boards = data.sponsor_boards || { boards: 0 };
  const pages = Math.max(1, Math.ceil(data.total / data.page_size));
  return (
    <>
      <div className="page-title">
        <div>
          <div className="eyebrow">EVERY US ROLE YOUR SEARCHES READ</div>
          <h1>Sponsorship Tracker</h1>
          <p>
            One row per entry-level role in your four tracks, with what the posting says about sponsorship
            (quoted), the employer's USCIS H-1B record and advertised pay. Published facts, not immigration advice.
          </p>
        </div>
        <a className="secondary" href={"/api/v2/tracker.csv?" + query(filters)} download>
          <Download size={17} /> Export CSV
        </a>
      </div>
      <div className="metrics">
        {[
          [Radar, s.postings, "Roles read (last 60 days)"],
          [Building2, s.employers, "Employers"],
          [ShieldCheck, s.with_h1b_record, "At employers with an H-1B record"],
          [ShieldX, s.refusing, "Refuse sponsorship (hidden)"],
        ].map(([Icon, value, label]: any) => (
          <section className="card metric" key={label}>
            <span className="metric-icon">
              <Icon size={20} />
            </span>
            <strong>{value}</strong>
            <span>{label}</span>
          </section>
        ))}
      </div>
      <p className="muted">
        {boards.boards
          ? `The morning search reads your tracked companies plus ${boards.boards} career boards of proven H-1B sponsors` +
            ` (registry checked ${boards.verified_on || "recently"}; ${boards.read_ever || 0} read so far, oldest first).`
          : "No H-1B sponsor-board registry yet: searches read your tracked companies only."}
        {s.says_sponsors ? ` ${s.says_sponsors} postings say outright that they sponsor.` : ""}
      </p>
      <div className="list-toolbar">
        <div className="search-input">
          <Search size={18} />
          <input
            aria-label="Search the tracker"
            placeholder="Company, role or city…"
            value={typed}
            onChange={(e) => setTyped(e.target.value)}
          />
        </div>
        <select aria-label="Sponsorship tier" value={filters.tier} onChange={set("tier")}>
          <option value="">All tiers</option>
          {["S", "A", "B", "C"].map((t) => (
            <option key={t} value={t}>
              {TIER_TEXT[t]}
            </option>
          ))}
        </select>
        <select aria-label="What the posting says" value={filters.statement} onChange={set("statement")}>
          <option value="">Any sponsorship wording</option>
          <option value="supports">Says it sponsors</option>
          <option value="silent">Silent</option>
          <option value="refuses">Will not sponsor</option>
          <option value="cannot_hire">Requires citizenship / clearance</option>
        </select>
        <select aria-label="H-1B record" value={filters.h1b} onChange={set("h1b")}>
          <option value="">Any H-1B record</option>
          <option value="record">Has H-1B approvals</option>
          <option value="none">No H-1B record</option>
        </select>
        <select aria-label="Minimum pay" value={filters.min_pay} onChange={set("min_pay")}>
          <option value="">Any pay</option>
          {[60000, 80000, 100000, 120000].map((n) => (
            <option key={n} value={n}>
              Pays {money(n)}+
            </option>
          ))}
        </select>
        <select aria-label="Found via" value={filters.source} onChange={set("source")}>
          <option value="">All sources</option>
          <option value="tracked">Tracked companies</option>
          <option value="sponsor_board">H-1B sponsor boards</option>
          <option value="ai_search">AI web search</option>
        </select>
        <select aria-label="Search decision" value={filters.outcome} onChange={set("outcome")}>
          <option value="">Any decision</option>
          <option value="not_selected">Passed, not saved yet</option>
          <option value="saved">Saved</option>
          <option value="relevance">Below fit threshold</option>
          <option value="reapply">Never-re-apply rule</option>
          <option value="legitimacy">Employer needs a check</option>
        </select>
        <select aria-label="Seen within" value={filters.seen_within} onChange={set("seen_within")}>
          <option value="">Any time</option>
          <option value="1">Seen today</option>
          <option value="7">Last 7 days</option>
          <option value="30">Last 30 days</option>
        </select>
        <select aria-label="Sort" value={filters.sort} onChange={set("sort")}>
          <option value="best">Best sponsorship odds</option>
          <option value="fit">Best fit</option>
          <option value="newest">Newest first</option>
          <option value="pay">Highest pay</option>
          <option value="h1b">Most H-1B approvals</option>
        </select>
        <label className="check-line">
          <input
            type="checkbox"
            checked={filters.hide_refusing !== "1"}
            onChange={(e) => setFilters({ ...filters, hide_refusing: e.target.checked ? "0" : "1" })}
          />
          Show refusing
        </label>
        <label className="check-line">
          <input
            type="checkbox"
            checked={!!filters.show_applied}
            onChange={(e) => setFilters({ ...filters, show_applied: e.target.checked ? "1" : "" })}
          />
          Show applied
        </label>
        <span className="muted">{data.total} roles</span>
      </div>
      {!data.items.length ? (
        <Empty title={s.postings ? "No roles in this view" : "Nothing read yet"}>
          {s.postings
            ? "Try another filter."
            : "Run a search from Daily Search (the 'portals' mix reads every tracked company and H-1B sponsor board with no AI call). Each role it reads appears here."}
        </Empty>
      ) : (
        <div className="job-list">
          {data.items.map((r) => {
            const saveable = !r.mine && !["refuses", "cannot_hire"].includes(r.statement);
            return (
              <div key={r.key} className="job-row tracker-row">
                <div className="job-open">
                  <span className="company-avatar">{r.company.slice(0, 2).toUpperCase()}</span>
                  <span className="job-main">
                    <strong>{r.title}</strong>
                    <span>
                      {r.company} <span className="job-location">· {r.location || "United States"}</span>
                    </span>
                    {r.sentence && (
                      <small className="tracker-quote">“{r.sentence}”</small>
                    )}
                    <small className="muted">
                      {r.outcome_label}
                      {r.outcome_reason && r.outcome_reason !== r.outcome_label ? ` — ${r.outcome_reason}` : ""} ·{" "}
                      {r.source_label} · first seen {day(r.first_seen)}
                      {r.posted_at ? ` · posted ${r.posted_at}` : ""}
                    </small>
                  </span>
                  <span className="job-meta">
                    <Badge tone={tierTone(r.tier)} title="Sponsorship tier">
                      {TIER_TEXT[r.tier] || r.tier}
                    </Badge>
                    <Badge tone={statementTone(r.statement)} title="What the posting says">
                      {r.statement_label}
                    </Badge>
                    {r.h1b_approvals > 0 && (
                      <Badge
                        tone="lime"
                        title={`USCIS H-1B Employer Data Hub: ${r.h1b_name}, FY ${r.h1b_years}; ${r.h1b_denials} denials`}
                      >
                        H-1B {r.h1b_approvals.toLocaleString()} approvals
                      </Badge>
                    )}
                    {r.everify ? <Badge title="E-Verify matters for the STEM OPT extension">E-Verify</Badge> : null}
                    {r.pay_max ? (
                      <Badge title={r.pay_text}>
                        {money(r.pay_min || r.pay_max)}–{money(r.pay_max)}
                      </Badge>
                    ) : null}
                    {typeof r.fit_score === "number" && (
                      <Badge tone={r.fit_score >= 70 ? "green" : r.fit_score >= 50 ? "amber" : "neutral"}>
                        Fit {r.fit_score}
                      </Badge>
                    )}
                    {r.mine && (
                      <Badge tone="green">
                        {r.mine === "removed" ? "Removed by you" : "Yours · " + (statusLabel[r.mine] || r.mine)}
                      </Badge>
                    )}
                  </span>
                </div>
                <span className="job-row-actions">
                  <a className="secondary" href={safeUrl(r.url)} target="_blank" rel="noreferrer">
                    Open posting <ArrowUpRight size={15} />
                  </a>
                  {saveable && (
                    <button type="button" className="secondary" disabled={saving === r.key} onClick={() => save(r)}>
                      {saving === r.key ? "Saving…" : "Save to my jobs"}
                    </button>
                  )}
                </span>
              </div>
            );
          })}
        </div>
      )}
      {pages > 1 && (
        <div className="list-toolbar">
          <button className="secondary" disabled={page <= 1} onClick={() => setPage(page - 1)}>
            Previous
          </button>
          <span className="muted">
            Page {page} of {pages}
          </span>
          <button className="secondary" disabled={page >= pages} onClick={() => setPage(page + 1)}>
            Next
          </button>
        </div>
      )}
    </>
  );
}
