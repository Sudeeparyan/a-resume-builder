import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Activity,
  ArrowDown,
  BookOpen,
  Bot,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  ClipboardList,
  Cpu,
  Download,
  ExternalLink,
  FileText,
  LoaderCircle,
  Mail,
  MessageSquare,
  Network,
  RotateCcw,
  ScanSearch,
  Search,
  Send,
  ShieldCheck,
  Sparkles,
  UserRound,
  Workflow,
  X,
  XCircle,
} from "lucide-react";
import type { ComponentType } from "react";
import { api, fileUrl, safeUrl } from "../api";
import { Badge, RichText } from "../components/UI";
import type {
  AssistantAgent,
  AssistantMessage,
  AssistantOverview,
  AssistantStep,
  Run,
  Summary,
} from "../types";
import { tierTitle } from "../components/JobList";

type Props = {
  data: Summary;
  refresh: () => Promise<void>;
  notify: (text: string, error?: boolean) => void;
  onJob: (id: string) => void;
};

/** What the front page offers: each is a real message the agent understands. */
const STARTERS: { label: string; hint: string; send?: string }[] = [
  { label: "Paste a posting", hint: "The whole job description plus its link; the one-page PDF comes back." },
  { label: "Search jobs for my profile", hint: "Today's search through the tracked career pages and portals.", send: "find jobs" },
  { label: "Which saved jobs still have no resume? Build them", hint: "Every draft goes through the one-page fit and the scorer." },
  { label: "What did I apply to this week, and what's still waiting?", hint: "Read from the tracker; nothing changes." },
  { label: "Research the newest saved job and write its study plan", hint: "Company research, the independent hiring review, then the plan." },
  { label: "Show my open profile questions", hint: "The answers that sharpen every future resume." },
];
const ALSO = ["status", "set my weekly target to 12", "how does the sponsorship rule work?", "excluded"];

const PENDING_LABEL: Record<string, string> = {
  posting_link: "Waiting for the posting link",
  posting_fields: "Waiting for Company | Job title | Location",
  confirm_applied: "Waiting for yes or no",
  confirm_tool: "Waiting for your yes before it changes anything",
  choose_job: "Waiting for you to pick a posting",
  agent: "Waiting for your answer",
};

/** Icon, short name and the message a click on the rail pre-fills, per registry agent.
 *  A prompt ending in a space wants a job or company name typed after it. */
const AGENT_UI: Record<string, { icon: ComponentType<{ size?: number }>; short: string; prompt: string }> = {
  assistant: { icon: Bot, short: "Assistant", prompt: "help" },
  orchestrator: { icon: Cpu, short: "Orchestrator", prompt: "what is running right now?" },
  sponsorship: { icon: ShieldCheck, short: "Sponsorship gate", prompt: "excluded" },
  reapply: { icon: ShieldCheck, short: "Never re-apply", prompt: "which companies are off limits right now and why?" },
  discovery: { icon: Search, short: "Job discovery", prompt: "find jobs" },
  resume: { icon: FileText, short: "Resume Studio", prompt: "build the resume for " },
  resume_match: { icon: ScanSearch, short: "Resume scorer", prompt: "score the resume for " },
  resume_advisor: { icon: FileText, short: "Resume advisor", prompt: "resume advice for " },
  resume_tracker: { icon: ClipboardList, short: "Tracker", prompt: "status" },
  research: { icon: Network, short: "Company research", prompt: "research " },
  hiring: { icon: UserRound, short: "Hiring review", prompt: "research " },
  match: { icon: ScanSearch, short: "Profile comparison", prompt: "research " },
  study_plan: { icon: BookOpen, short: "Study planner", prompt: "study plan for " },
  profile: { icon: UserRound, short: "Profile curator", prompt: "show my pending profile entries" },
  email: { icon: Mail, short: "Email evidence", prompt: "which application emails are waiting for me?" },
  instruction_tracker: { icon: MessageSquare, short: "Instruction chat", prompt: "open " },
};
/** Which registry agents a background run of each kind lights up. */
const RUN_AGENTS: Record<string, string[]> = {
  research: ["research", "hiring", "match"],
  resume_advisor: ["resume_advisor"],
  discovery: ["discovery", "sponsorship", "reapply"],
  resume_build: ["resume", "resume_match"],
  resume_match: ["resume_match"],
  study_plan: ["study_plan"],
  email: ["email"],
  instruction_interpret: ["instruction_tracker"],
};
const RUN_LABEL: Record<string, string> = {
  research: "Company & hiring review",
  resume_advisor: "Resume advisor",
  email: "Gmail sync",
  discovery: "Job discovery",
  resume_build: "Resume build & score",
  resume_match: "Independent review",
  instruction_interpret: "Instruction interpreter",
  study_plan: "Study plan",
};
/** The pipeline a pasted posting goes through, shown before the first message. */
const DEFAULT_FLOW = ["assistant", "sponsorship", "resume", "resume_match"];
/** Rail order: the chat's own path first, then the agents it starts, then the plumbing. */
const RAIL_ORDER = [
  "assistant", "sponsorship", "reapply", "discovery", "resume", "resume_match", "research", "hiring", "match",
  "study_plan", "resume_advisor", "profile", "resume_tracker", "email", "orchestrator", "instruction_tracker",
];

/** Polling: quick while a reply is being worked on, relaxed when idle, slow in a hidden tab. */
const POLL_BUSY = 1200;
const POLL_IDLE = 8000;
const POLL_HIDDEN = 30000;

const active = (state: string) => state === "queued" || state === "running";

function requestId() {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID().replace(/-/g, "")
    : Date.now().toString(36) + Math.random().toString(36).slice(2);
}

/** "18:30" in the reader's own clock. */
export function clock(iso: string): string {
  const at = new Date(iso);
  return isNaN(at.getTime()) ? "" : at.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

/** "12 s", "1 m 05 s": how long an exchange took. */
export function elapsed(seconds: number): string {
  const s = Math.max(0, Math.round(seconds));
  if (s < 60) return s + " s";
  return Math.floor(s / 60) + " m " + String(s % 60).padStart(2, "0") + " s";
}

/** The one-tap answers a pending question accepts, so a yes never needs typing. */
export function quickReplies(pending: AssistantOverview["pending"]): { label: string; send: string }[] {
  if (!pending) return [];
  if (pending.kind === "confirm_tool" || pending.kind === "confirm_applied") {
    return [
      { label: "Yes, go ahead", send: "yes" },
      { label: "No, skip it", send: "no" },
    ];
  }
  if (pending.kind === "choose_job") {
    return (pending.candidates || []).slice(0, 6).map((c, i) => ({
      label: `${i + 1}. ${c.company} — ${c.title}`,
      send: String(i + 1),
    }));
  }
  return [];
}

/** Whether the reader is close enough to the bottom for new activity to keep them there. */
function nearBottom() {
  const root = document.documentElement;
  return window.innerHeight + window.scrollY >= root.scrollHeight - 140;
}

/** The true end of the page: there the sticky composer sits below the thread, hiding nothing. */
function scrollToEnd(behavior: ScrollBehavior) {
  window.scrollTo({ top: document.documentElement.scrollHeight, behavior });
}

export default function Assistant({ data, refresh, notify, onJob }: Props) {
  const [overview, setOverview] = useState<AssistantOverview>();
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  // The message just sent, shown at once while the server records it.
  const [echo, setEcho] = useState<{ id: string; text: string; at: string } | null>(null);
  const [error, setError] = useState("");
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [stepsOpen, setStepsOpen] = useState<Record<string, boolean>>({});
  const [railOpen, setRailOpen] = useState(false);
  const [unseen, setUnseen] = useState(false);
  const [now, setNow] = useState(() => Date.now());
  const boxRef = useRef<HTMLTextAreaElement>(null);
  // Which messages were still processing at the last poll: when one settles,
  // the rest of the app is refreshed so every tab shows what the chat changed.
  const processing = useRef<Set<string>>(new Set());
  // Every load carries a sequence number: a slow poll that lands after a newer
  // one is dropped, so the thread never flicks back to an older state.
  const seq = useRef(0);
  const timer = useRef(0);
  const alive = useRef(true);
  const tickRef = useRef<() => Promise<void>>(async () => {});
  // The reader is at the bottom of the thread, so new activity may scroll it.
  const stick = useRef(true);
  const firstScroll = useRef(true);
  // While the page scrolls itself (smoothly) the passing positions are not the
  // reader's choice, so they must not turn the pinning off.
  const autoUntil = useRef(0);
  // On a phone the keyboard's Enter is a new line; the Send button sends.
  const touch = useMemo(() => typeof matchMedia === "function" && matchMedia("(pointer: coarse)").matches, []);

  const load = useCallback(async () => {
    const n = ++seq.current;
    const next = await api<AssistantOverview>("/v2/assistant", "GET", undefined, { timeout: 20000 });
    if (n !== seq.current || !alive.current) return next;
    const settled = next.messages.filter(
      (m) => processing.current.has(m.id) && m.state !== "processing",
    );
    processing.current = new Set(
      next.messages.filter((m) => m.state === "processing").map((m) => m.id),
    );
    setOverview(next);
    setEcho((e) => (e && next.messages.some((m) => m.id === e.id) ? null : e));
    if (settled.length) {
      await refresh().catch(() => {});
      for (const m of settled)
        if (m.state === "failed") notify(m.response, true);
    }
    return next;
  }, [refresh, notify]);

  const schedule = useCallback((ms: number) => {
    if (!alive.current) return;
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => void tickRef.current(), ms);
  }, []);

  const tick = useCallback(async () => {
    if (!alive.current) return;
    let busy = false;
    try {
      busy = (await load()).busy;
      if (alive.current) setError("");
    } catch (e) {
      if (alive.current) setError((e as Error).message);
    }
    schedule(busy ? POLL_BUSY : document.visibilityState === "hidden" ? POLL_HIDDEN : POLL_IDLE);
  }, [load, schedule]);
  tickRef.current = tick;

  useEffect(() => {
    alive.current = true;
    void tickRef.current();
    // Coming back to the tab (or the window) checks at once instead of waiting out a long timer.
    const wake = () => {
      if (document.visibilityState === "visible") void tickRef.current();
    };
    document.addEventListener("visibilitychange", wake);
    window.addEventListener("focus", wake);
    const onScroll = () => {
      if (autoUntil.current > Date.now()) {
        if (nearBottom()) autoUntil.current = 0;
        return;
      }
      stick.current = nearBottom();
      if (stick.current) setUnseen(false);
    };
    // A wheel or a finger is the reader: it ends any scroll the page started.
    const onGesture = () => {
      autoUntil.current = 0;
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("wheel", onGesture, { passive: true });
    window.addEventListener("touchmove", onGesture, { passive: true });
    return () => {
      alive.current = false;
      seq.current++;
      window.clearTimeout(timer.current);
      document.removeEventListener("visibilitychange", wake);
      window.removeEventListener("focus", wake);
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("wheel", onGesture);
      window.removeEventListener("touchmove", onGesture);
    };
  }, []);

  const messages = overview?.messages || [];
  const latest = messages[messages.length - 1];
  const working = !!echo || latest?.state === "processing";
  // A once-a-second clock only while something is being worked on, for the elapsed time.
  useEffect(() => {
    if (!working) return;
    const clockTimer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(clockTimer);
  }, [working]);

  // Only real changes to the thread move the page: a new exchange, a step, a settled
  // reply. A reader who scrolled up keeps their place and gets a "new activity" nudge.
  const loaded = !!overview;
  const count = messages.length;
  const lastState = latest?.state;
  const lastSteps = latest?.steps.length;
  const echoId = echo?.id;
  useEffect(() => {
    if (!loaded || (count === 0 && !echoId)) return; // the welcome card reads from the top
    if (stick.current) {
      autoUntil.current = Date.now() + 1500;
      scrollToEnd(firstScroll.current ? "auto" : "smooth");
      if (firstScroll.current) {
        // Fonts and previews that land after the first paint make the thread taller.
        document.fonts?.ready.then(() => stick.current && scrollToEnd("auto")).catch(() => {});
      }
      firstScroll.current = false;
    } else if (count || echoId) {
      setUnseen(true);
    }
  }, [loaded, count, lastState, lastSteps, echoId]);

  function jumpToLatest() {
    stick.current = true;
    setUnseen(false);
    autoUntil.current = Date.now() + 1500;
    scrollToEnd("smooth");
  }

  async function send(text: string) {
    const message = text.trim();
    if (!message || sending) return;
    const id = requestId();
    setSending(true);
    setError("");
    setEcho({ id, text: message, at: new Date().toISOString() });
    setDraft("");
    if (boxRef.current) boxRef.current.style.height = "";
    stick.current = true;
    setUnseen(false);
    try {
      await api("/v2/assistant/messages", "POST", { message, request_id: id });
      await load();
      schedule(POLL_BUSY);
    } catch (e) {
      setEcho(null);
      setDraft(message);
      setError((e as Error).message);
    } finally {
      setSending(false);
    }
  }

  /** A rail click pre-fills the composer and never sends: a tap on a list is not a request.
   *  A complete message is one Enter away; one that needs a job name waits for it. */
  function prompt(text: string) {
    setRailOpen(false);
    setDraft(text);
    const box = boxRef.current;
    if (box) {
      grow(box);
      box.focus();
      window.setTimeout(() => {
        box.setSelectionRange(text.length, text.length);
        grow(box);
      }, 0);
    }
  }

  async function chooseEngine(value: string) {
    const [provider, model] = value.split("::");
    try {
      await api("/v2/ai/main", "PUT", { provider, model });
      await load();
      notify("Everything now runs on " + (overview?.engine.options.find((o) => o.provider === provider && o.model === model)?.label || model));
    } catch (e) {
      notify((e as Error).message, true);
    }
  }

  function grow(el: HTMLTextAreaElement) {
    el.style.height = "";
    el.style.height = Math.min(el.scrollHeight, 260) + "px";
  }

  const jobs = new Map(data.jobs.map((j) => [j.id, j]));
  const runningNow = data.runs.filter((r) => active(r.state)).length;
  const current = latest?.state === "processing" ? latest.steps[latest.steps.length - 1] : undefined;
  const startedAt = echo ? new Date(echo.at).getTime() : latest?.state === "processing" ? new Date(latest.created_at).getTime() : 0;
  const quick = quickReplies(overview?.pending ?? null);
  const names = new Map(overview?.agents.map((a) => [a.id, AGENT_UI[a.id]?.short || a.name]));
  return (
    <div className="chat chat-with-rail">
      <div className="chat-main">
        <div className="page-title chat-title">
          <div>
            <div className="eyebrow">ONE PLACE TO TALK TO YOUR WORKSPACE</div>
            <h1>Assistant</h1>
            <p>
              Paste a posting and get the one-page PDF back, or ask for anything in plain words:
              the agent does it with the same tools the tabs use, asks before anything hard to undo,
              and never submits for you.
            </p>
          </div>
          <div className="chat-title-side">
            {overview && !overview.ai_configured && (
              <Badge tone="amber" title="Install Claude Code or the ChatGPT app, or add a provider key in Settings">
                No AI runtime · shortcuts only
              </Badge>
            )}
            <button
              type="button"
              className="secondary chat-rail-toggle"
              onClick={() => setRailOpen(true)}
              aria-label="Show the agents"
            >
              <Workflow size={15} /> Agents
              {(working || runningNow > 0) && <span className="rail-live" aria-label="working" />}
            </button>
          </div>
        </div>
        {error && (
          <div className="callout warning" role="alert">
            {error}
          </div>
        )}
        <div className="chat-thread" aria-live="polite">
          {!overview ? (
            <p className="muted chat-loading">
              <LoaderCircle className="spin" size={15} /> Loading the conversation…
            </p>
          ) : messages.length === 0 && !echo ? (
            <section className="card chat-welcome">
              <span className="metric-icon">
                <Sparkles size={20} />
              </span>
              <h2>What would you like done?</h2>
              <div className="chat-starters">
                {STARTERS.map((s) => (
                  <button
                    key={s.label}
                    className="chat-starter"
                    onClick={() =>
                      s.label === "Paste a posting" ? boxRef.current?.focus() : send(s.send || s.label)
                    }
                  >
                    <b>{s.label}</b>
                    <span>{s.hint}</span>
                  </button>
                ))}
              </div>
              <div className="chat-also">
                <span className="muted">Also try</span>
                {ALSO.map((s) => (
                  <button key={s} type="button" className="chip" onClick={() => send(s)}>
                    {s}
                  </button>
                ))}
              </div>
            </section>
          ) : (
            messages.map((m) => (
              <Exchange
                key={m.id}
                message={m}
                names={names}
                expanded={!!expanded[m.id]}
                onExpand={() => setExpanded({ ...expanded, [m.id]: !expanded[m.id] })}
                stepsOpen={stepsOpen[m.id]}
                onSteps={(open) => setStepsOpen({ ...stepsOpen, [m.id]: open })}
                onJob={onJob}
                onSend={send}
                now={now}
                jobTier={m.data.job_id ? jobs.get(m.data.job_id)?.sponsor_tier : undefined}
              />
            ))
          )}
          {echo && (
            <>
              <article className="chat-bubble you echo">
                <div className="chat-text">{echo.text.length > 700 ? echo.text.slice(0, 700) + "…" : echo.text}</div>
                <div className="chat-when">Sending…</div>
              </article>
              <article className="chat-bubble assistant processing" aria-busy="true">
                <p className="muted chat-wait">
                  <LoaderCircle className="spin" size={15} /> Working on it…
                </p>
              </article>
            </>
          )}

        </div>
        <form
          className="chat-composer"
          onSubmit={(e) => {
            e.preventDefault();
            void send(draft);
          }}
        >
          {unseen && (
            <button type="button" className="chat-jump" onClick={jumpToLatest}>
              <ArrowDown size={14} /> New activity
            </button>
          )}
          {working ? (
            <div className="chat-working" role="status">
              <span className="rail-live" aria-hidden="true" />
              <span className="chat-working-label">
                {current ? current.label : "Working on it"}
                {current?.agent && current.agent !== "assistant" && (
                  <em className="chat-step-agent">{names.get(current.agent) || current.agent}</em>
                )}
              </span>
              {startedAt > 0 && <small>{elapsed((now - startedAt) / 1000)}</small>}
            </div>
          ) : (
            overview?.pending && (
              <div className="chat-pending-row">
                <div className="chat-pending">
                  <MessageSquare size={14} />
                  {PENDING_LABEL[overview.pending.kind] || "Waiting for your answer"}
                  <button type="button" className="text-button" onClick={() => send("cancel")}>
                    Cancel
                  </button>
                </div>
                {quick.length > 0 && (
                  <div className="chat-quick" aria-label="Quick answers">
                    {quick.map((q) => (
                      <button key={q.send} type="button" className={"chip" + (q.send === "yes" ? " yes" : "")} onClick={() => send(q.send)}>
                        {q.send === "yes" && <CheckCircle2 size={13} />}
                        {q.label}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )
          )}
          <div className="chat-input">
            <textarea
              ref={boxRef}
              rows={1}
              placeholder={touch ? "Paste a posting or ask for anything…" : "Paste a job description with its link, or ask for anything…"}
              value={draft}
              maxLength={120000}
              aria-label="Message the assistant"
              enterKeyHint="send"
              onChange={(e) => {
                setDraft(e.target.value);
                grow(e.target);
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey && !touch && !e.nativeEvent.isComposing) {
                  e.preventDefault();
                  void send(draft);
                }
              }}
            />
            <button className="primary" disabled={sending || !draft.trim()} aria-label="Send">
              {sending ? <LoaderCircle className="spin" size={18} /> : <Send size={18} />}
            </button>
          </div>
          <small className="muted chat-hint">
            {touch ? "Long pastes are fine" : "Enter sends · Shift+Enter for a new line · long pastes are fine"}
          </small>
        </form>
      </div>
      {overview && (
        <AgentRail
          overview={overview}
          data={data}
          latest={latest}
          open={railOpen}
          onClose={() => setRailOpen(false)}
          onPrompt={prompt}
          onEngine={chooseEngine}
        />
      )}
    </div>
  );
}

type FlowNode = {
  id: string;
  state: "done" | "running" | "failed" | "idle";
  detail: string;
  run?: Run;
};

/** The real chain behind the latest message: one node per agent, in the order its steps ran. */
export function flowFor(latest: AssistantMessage | undefined, runs: Run[]): { nodes: FlowNode[]; live: boolean } {
  if (!latest || latest.steps.length === 0) {
    return { nodes: DEFAULT_FLOW.map((id) => ({ id, state: "idle", detail: "" })), live: false };
  }
  const byId = new Map<string, FlowNode>();
  for (const step of latest.steps) {
    const id = step.agent || "assistant";
    const run = step.run_id ? runs.find((r) => r.id === step.run_id) : undefined;
    let state: FlowNode["state"] = step.state;
    let detail = step.detail;
    if (run && active(run.state)) {
      state = "running";
      detail = RUN_LABEL[run.kind] + " · " + (run.result?.stage || run.state);
    } else if (run && run.state === "failed") {
      state = "failed";
      detail = run.error || detail;
    }
    const node = byId.get(id);
    if (node) {
      // A later step on the same agent updates it, but a running one always wins.
      if (node.state !== "running") Object.assign(node, { state, detail, run: run || node.run });
    } else byId.set(id, { id, state, detail, run });
  }
  const nodes = [...byId.values()];
  return { nodes, live: latest.state === "processing" || nodes.some((n) => n.state === "running") };
}

export function AgentRail({
  overview,
  data,
  latest,
  open,
  onClose,
  onPrompt,
  onEngine,
}: {
  overview: AssistantOverview;
  data: Summary;
  latest?: AssistantMessage;
  open: boolean;
  onClose: () => void;
  onPrompt: (text: string) => void;
  onEngine: (value: string) => void;
}) {
  const agents = useMemo(() => new Map(overview.agents.map((a) => [a.id, a])), [overview.agents]);
  const runs = data.runs;
  const running = runs.filter((r) => active(r.state));
  const lit = new Set<string>();
  for (const r of running) for (const id of RUN_AGENTS[r.kind] || []) lit.add(id);
  const { nodes, live } = flowFor(latest, runs);
  // A reply that used no tools (help, a shortcut) leaves the pipeline preview in place.
  const real = !!latest && latest.steps.length > 0;
  for (const n of nodes) if (n.state === "running") lit.add(n.id);
  if (overview.busy) lit.add("assistant");
  const jobName = (id: string | null) => {
    const job = id ? data.jobs.find((j) => j.id === id) : undefined;
    return job ? job.company : "";
  };
  const engine = overview.engine;
  const current = engine.provider + "::" + engine.model;
  const listed = engine.options.some((o) => o.provider + "::" + o.model === current);
  const runsElsewhere = engine.runs && (engine.runs.provider !== engine.provider || engine.runs.model !== engine.model);
  // Escape closes the drawer on narrow screens.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);
  return (
    <>
      {open && <div className="rail-backdrop" onClick={onClose} aria-hidden="true" />}
      <div className={"agent-rail" + (open ? " open" : "")} role="complementary" aria-label="Agents">
        <div className="rail-head">
          <div>
            <div className="eyebrow">AGENTS</div>
            <h2>Linked to this chat</h2>
          </div>
          <button type="button" className="icon-button rail-close" aria-label="Hide the agents" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <section className="rail-section rail-engine">
          <label>
            <span className="rail-label">
              <Cpu size={13} /> Runs on
            </span>
            <select value={listed ? current : ""} onChange={(e) => e.target.value && onEngine(e.target.value)} aria-label="AI runtime for the assistant and the runs it starts">
              {!listed && <option value="">{engine.label}{engine.ready ? "" : " (not ready)"}</option>}
              {engine.options.map((o) => (
                <option key={o.provider + "::" + o.model} value={o.provider + "::" + o.model}>
                  {o.label}
                </option>
              ))}
            </select>
          </label>
          {engine.moved_from && (
            <small className="muted">{engine.moved_from} is not ready on this Mac, so {engine.label.split(" · ")[0]} answers the chat.</small>
          )}
          {runsElsewhere && (
            <small className={engine.runs.ready ? "muted" : "rail-warn"}>
              Background runs go through {engine.runs.label}{engine.runs.ready ? "" : ", which is not ready"}. Pick a runtime above to use one engine for everything.
            </small>
          )}
          {engine.note && <small className="rail-warn">{engine.note}</small>}
          {!engine.ready && !engine.moved_from && (
            <small className="rail-warn">Nothing is ready: install Claude Code or the ChatGPT app, or add a key in Settings.</small>
          )}
        </section>

        <section className="rail-section">
          <div className="rail-label">
            <Workflow size={13} /> {real ? (live ? "Live flow" : "Last flow") : "What a pasted posting goes through"}
            {live && <span className="rail-live" aria-label="working" />}
          </div>
          <ol className={"rail-flow" + (live ? " live" : "")}>
            {nodes.map((n, i) => {
              const ui = AGENT_UI[n.id] || { icon: Bot, short: agents.get(n.id)?.name || n.id, prompt: "help" };
              const Icon = ui.icon;
              const next = nodes[i + 1];
              return (
                <li key={n.id} className={"rail-node " + n.state} style={{ animationDelay: i * 60 + "ms" }}>
                  <div className="rail-dot" aria-hidden="true">
                    {n.state === "running" ? <LoaderCircle className="spin" size={14} /> : n.state === "failed" ? <XCircle size={14} /> : n.state === "done" ? <CheckCircle2 size={14} /> : <Icon size={14} />}
                  </div>
                  <div className="rail-body">
                    <b>{ui.short}</b>
                    {n.detail && <small>{n.detail}</small>}
                  </div>
                  {next && <span className={"rail-link" + (n.state === "running" || next.state === "running" || (live && n.state === "done" && next.state !== "done") ? " active" : "")} aria-hidden="true" />}
                </li>
              );
            })}
          </ol>
        </section>

        <section className="rail-section">
          <div className="rail-label">
            <Activity size={13} /> Running now
          </div>
          {running.length === 0 ? (
            <p className="muted rail-empty">No agent is running. Start one from the chat or the list below.</p>
          ) : (
            <ul className="rail-runs">
              {running.map((r) => (
                <li key={r.id}>
                  <LoaderCircle className="spin" size={13} />
                  <div>
                    <b>{RUN_LABEL[r.kind] || r.kind}</b>
                    <small>{[jobName(r.job_id), r.result?.stage || r.state].filter(Boolean).join(" · ")}</small>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="rail-section">
          <div className="rail-label">
            <Bot size={13} /> All agents
          </div>
          <ul className="rail-agents">
            {[...overview.agents]
              .sort((a, b) => (RAIL_ORDER.indexOf(a.id) + 1 || 99) - (RAIL_ORDER.indexOf(b.id) + 1 || 99))
              .map((a) => (
                <AgentRow key={a.id} agent={a} active={lit.has(a.id)} onPrompt={onPrompt} />
              ))}
          </ul>
          <a className="rail-more" href="#agents">
            Every run, stage and AI call on the Agents tab →
          </a>
        </section>
      </div>
    </>
  );
}

function AgentRow({ agent, active: isActive, onPrompt }: { agent: AssistantAgent; active: boolean; onPrompt: (text: string) => void }) {
  const ui = AGENT_UI[agent.id] || { icon: Bot, short: agent.name, prompt: "help" };
  const Icon = ui.icon;
  const title = agent.does + (agent.tools.length ? "\n\nFrom the chat: " + agent.tools.join(", ") : "");
  return (
    <li className={"rail-agent" + (isActive ? " active" : "") + (agent.linked ? "" : " unlinked")}>
      <button
        type="button"
        title={title}
        disabled={!agent.linked}
        onClick={() => onPrompt(ui.prompt)}
      >
        <span className="rail-agent-icon">
          <Icon size={15} />
        </span>
        <span className="rail-agent-name">
          <b>{ui.short}</b>
          <small>{isActive ? "active now" : agent.linked ? "linked" : "Agents tab only"}</small>
        </span>
        <span className={"rail-status" + (isActive ? " on" : agent.linked ? " linked" : "")} aria-hidden="true" />
      </button>
    </li>
  );
}

export function Exchange({
  message: m,
  names,
  expanded,
  onExpand,
  stepsOpen,
  onSteps,
  onJob,
  onSend,
  now,
  jobTier,
}: {
  message: AssistantMessage;
  names: Map<string, string>;
  expanded: boolean;
  onExpand: () => void;
  stepsOpen?: boolean;
  onSteps: (open: boolean) => void;
  onJob: (id: string) => void;
  onSend: (text: string) => void;
  now: number;
  jobTier?: string | null;
}) {
  const long = m.message.length > 700;
  const shown = long && !expanded ? m.message.slice(0, 700) + "…" : m.message;
  const working = m.state === "processing";
  const failed = m.state === "failed";
  // A result card only where there is a document to act on; a question or a
  // queued run just names the job in its text.
  const hasResult = !!m.data.pdf || m.data.intent === "open" || m.data.intent === "resume_ready";
  const tier = (m.data.tier || jobTier || "C") as string;
  const stepName = (step: AssistantStep) => (step.agent && step.agent !== "assistant" ? names.get(step.agent) : undefined);
  const started = new Date(m.created_at).getTime();
  const finished = new Date(m.updated_at).getTime();
  const took = working ? (now - started) / 1000 : (finished - started) / 1000;
  // Steps stay open while they happen and after a failure; a finished answer folds them away.
  const showSteps = stepsOpen ?? (working || failed);
  const stepSummary = m.steps.map((s) => s.label).filter((label, i, all) => all.indexOf(label) === i).slice(0, 3).join(" · ");
  return (
    <>
      <article className="chat-bubble you">
        <div className="chat-text">{shown}</div>
        {long && (
          <button type="button" className="text-button" onClick={onExpand}>
            {expanded ? "Show less" : `Show all ${m.message.length.toLocaleString()} characters`}
          </button>
        )}
        <div className="chat-when">{clock(m.created_at)}</div>
      </article>
      <article
        className={"chat-bubble assistant " + m.state}
        aria-busy={working}
      >
        {m.steps.length > 0 && (
          <>
            <button
              type="button"
              className="chat-steps-toggle"
              aria-expanded={showSteps}
              onClick={() => onSteps(!showSteps)}
            >
              {showSteps ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
              {working ? (
                <span>
                  {m.steps.length} {m.steps.length === 1 ? "step" : "steps"} so far · {elapsed(took)}
                </span>
              ) : (
                <span>
                  {m.steps.length} {m.steps.length === 1 ? "step" : "steps"} in {elapsed(took)}
                  {!showSteps && stepSummary && <em> — {stepSummary}{m.steps.length > 3 ? "…" : ""}</em>}
                </span>
              )}
            </button>
            {showSteps && (
              <ol className="chat-steps">
                {m.steps.map((step, n) => (
                  <li key={n} className={step.state}>
                    <span aria-hidden="true">
                      {step.state === "running" ? (
                        <LoaderCircle className="spin" size={15} />
                      ) : step.state === "failed" ? (
                        <XCircle size={15} />
                      ) : (
                        <CheckCircle2 size={15} />
                      )}
                    </span>
                    <div>
                      <b>
                        {step.label}
                        {stepName(step) && <em className="chat-step-agent">{stepName(step)}</em>}
                      </b>
                      {step.detail && <small>{step.detail}</small>}
                    </div>
                  </li>
                ))}
              </ol>
            )}
          </>
        )}
        {working && m.steps.length === 0 ? (
          <p className="muted chat-wait">
            <LoaderCircle className="spin" size={15} /> Working on it…
          </p>
        ) : (
          !working && <RichText text={m.response} />
        )}
        {failed && (
          <div className="chat-retry">
            <button type="button" className="secondary" onClick={() => onSend(m.message)}>
              <RotateCcw size={14} /> Try again
            </button>
          </div>
        )}
        {hasResult && !working && (
          <div className="chat-result">
            {m.data.preview_png && (
              <a
                className="chat-page"
                href={fileUrl(m.data.preview_png)}
                target="_blank"
                rel="noreferrer"
                title="Open the rendered page"
              >
                <img src={fileUrl(m.data.preview_png)} alt="Rendered resume page" />
              </a>
            )}
            <div className="chat-result-body">
              {m.data.company && (
                <div className="chat-result-title">
                  <FileText size={16} />
                  <b>
                    {m.data.company} — {m.data.title}
                  </b>
                  {(m.data.tier || jobTier) && (
                    <Badge
                      tone={tier === "S" ? "green" : tier === "A" ? "lime" : "neutral"}
                      title={tierTitle[tier as keyof typeof tierTitle]}
                    >
                      Tier {tier}
                    </Badge>
                  )}
                  {m.data.revision != null && <small>v{m.data.revision}</small>}
                </div>
              )}
              {(m.data.coverage != null || m.data.ats != null) && (
                <div className="chat-scores">
                  {m.data.coverage != null && (
                    <span>
                      <b>{m.data.coverage}</b> JD coverage
                    </span>
                  )}
                  {m.data.ats != null && (
                    <span>
                      <b>{m.data.ats}</b> ATS readiness
                    </span>
                  )}
                </div>
              )}
              <div className="chat-actions">
                {m.data.pdf && (
                  <a
                    className="primary"
                    href={fileUrl(m.data.pdf)}
                    download={
                      (m.data.company || "resume").replace(/\W+/g, "-") + "-resume.pdf"
                    }
                  >
                    <Download size={15} /> Download PDF
                  </a>
                )}
                {m.data.job_id && (
                  <button type="button" className="secondary" onClick={() => onJob(m.data.job_id!)}>
                    <FileText size={15} /> Open in Resume Studio
                  </button>
                )}
                {m.data.posting_url && (
                  <a
                    className="secondary"
                    href={safeUrl(m.data.posting_url)}
                    target="_blank"
                    rel="noreferrer"
                  >
                    <ExternalLink size={15} /> Open the posting
                  </a>
                )}
              </div>
            </div>
          </div>
        )}
        {!working && !!m.data.suggestions?.length && (
          <div className="chat-suggestions">
            {m.data.suggestions.map((s) => (
              <button key={s} type="button" className="chip" onClick={() => onSend(s)}>
                {s}
              </button>
            ))}
          </div>
        )}
        {!working && (
          <div className="chat-when">
            {failed ? "Failed" : "Answered"} at {clock(m.updated_at)}
          </div>
        )}
      </article>
    </>
  );
}
