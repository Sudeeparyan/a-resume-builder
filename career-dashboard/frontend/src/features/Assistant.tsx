import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Activity,
  ArrowDown,
  BookOpen,
  Bot,
  CalendarCheck,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  CircleHelp,
  ClipboardList,
  ClipboardPaste,
  Copy,
  Cpu,
  Download,
  ExternalLink,
  FileText,
  History,
  LoaderCircle,
  Mail,
  MessageSquare,
  Network,
  Pencil,
  RefreshCw,
  RotateCcw,
  ScanSearch,
  Search,
  Send,
  ShieldCheck,
  Sparkles,
  Square,
  SquarePen,
  Trash2,
  UserRound,
  Workflow,
  X,
  XCircle,
} from "lucide-react";
import type { ComponentType } from "react";
import { api, fileUrl, safeUrl } from "../api";
import { Badge, Modal, RichText } from "../components/UI";
import type {
  AssistantAgent,
  AssistantConversation,
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
const STARTERS: { label: string; hint: string; send?: string; icon: ComponentType<{ size?: number }> }[] = [
  { label: "Paste a posting", hint: "The whole job description plus its link; the one-page PDF comes back.", icon: ClipboardPaste },
  { label: "Search jobs for my profile", hint: "Today's search through the tracked career pages and portals.", send: "find jobs", icon: Search },
  { label: "Which saved jobs still have no resume? Build them", hint: "Every draft goes through the one-page fit and the scorer.", icon: FileText },
  { label: "What did I apply to this week, and what's still waiting?", hint: "Read from the tracker; nothing changes.", icon: CalendarCheck },
  { label: "Research the newest saved job and write its study plan", hint: "Company research, the independent hiring review, then the plan.", icon: BookOpen },
  { label: "Show my open profile questions", hint: "The answers that sharpen every future resume.", icon: CircleHelp },
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
/** A message longer than this folds until "Show all" is pressed. */
const FOLD_AT = 700;

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

/** "Today", "Yesterday", then "Mon, Sep 15" (with the year once it differs). */
const DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export function dayLabel(iso: string, now: Date = new Date()): string {
  const at = new Date(iso);
  if (isNaN(at.getTime())) return "";
  const midnight = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
  const days = Math.round((midnight(now) - midnight(at)) / 86_400_000);
  if (days === 0) return "Today";
  if (days === 1) return "Yesterday";
  // Fixed abbreviations: toLocaleDateString's short month is CLDR-dependent
  // ("Sep" vs "Sept"), so the same day rendered differently across machines.
  const base = `${DAY_NAMES[at.getDay()]}, ${MONTH_NAMES[at.getMonth()]} ${at.getDate()}`;
  return at.getFullYear() === now.getFullYear() ? base : `${base}, ${at.getFullYear()}`;
}

/** Whether an exchange mentions the search words (all of them, in either side). */
export function matches(m: Pick<AssistantMessage, "message" | "response">, query: string): boolean {
  const words = query.toLowerCase().split(/\s+/).filter(Boolean);
  if (!words.length) return true;
  const text = (m.message + "\n" + m.response).toLowerCase();
  return words.every((w) => text.includes(w));
}

/** The conversation as a Markdown file she can keep or send. */
export function exportMarkdown(title: string, messages: AssistantMessage[], now: Date = new Date()): string {
  const lines = [`# ${title}`, "", `Assistant chat exported ${now.toLocaleString()} · ${messages.length} ${messages.length === 1 ? "exchange" : "exchanges"}`, ""];
  for (const m of messages) {
    lines.push("---", "", `**You** · ${new Date(m.created_at).toLocaleString()}`, "", m.message, "");
    const state = m.state === "failed" ? " (failed)" : m.state === "processing" ? " (still working)" : "";
    lines.push(`**Assistant**${state} · ${new Date(m.updated_at).toLocaleString()}`, "", m.response, "");
    if (m.data.pdf) lines.push(`Resume PDF: ${m.data.pdf}`, "");
  }
  return lines.join("\n");
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

async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    // An older browser or a page without clipboard permission: the selection route still works.
    const box = document.createElement("textarea");
    box.value = text;
    box.setAttribute("readonly", "");
    box.style.position = "fixed";
    box.style.opacity = "0";
    document.body.appendChild(box);
    box.select();
    let ok = false;
    try {
      ok = document.execCommand("copy");
    } catch {
      ok = false;
    }
    box.remove();
    return ok;
  }
}

function greeting(now: Date = new Date()) {
  const h = now.getHours();
  return h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening";
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
  const [historyOpen, setHistoryOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [confirmDelete, setConfirmDelete] = useState<AssistantConversation | null>(null);
  const [confirmClear, setConfirmClear] = useState(false);
  const [stopping, setStopping] = useState(false);
  const [unseen, setUnseen] = useState(false);
  const [away, setAway] = useState(false);
  const [now, setNow] = useState(() => Date.now());
  const boxRef = useRef<HTMLTextAreaElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);
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
  const mac = useMemo(() => /Mac|iPhone|iPad/.test(navigator.userAgent || ""), []);
  const mod = mac ? "⌘" : "Ctrl+";

  /** A fresh overview from an action (new chat, open, delete) replaces whatever a slower poll would bring. */
  const adopt = useCallback((next: AssistantOverview) => {
    seq.current++;
    processing.current = new Set(next.messages.filter((m) => m.state === "processing").map((m) => m.id));
    setOverview(next);
  }, []);

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
        if (m.state === "failed" && m.data.intent !== "stopped") notify(m.response, true);
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
      const bottom = nearBottom();
      setAway(!bottom);
      if (autoUntil.current > Date.now()) {
        if (bottom) autoUntil.current = 0;
        return;
      }
      stick.current = bottom;
      if (bottom) setUnseen(false);
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
  // "Stopping…" ends when the reply does.
  useEffect(() => {
    if (!working) setStopping(false);
  }, [working]);

  // Only real changes to the thread move the page: a new exchange, a step, a settled
  // reply. A reader who scrolled up keeps their place and gets a "new activity" nudge.
  const loaded = !!overview;
  const count = messages.length;
  const lastState = latest?.state;
  const lastSteps = latest?.steps.length;
  const echoId = echo?.id;
  const conversationId = overview?.conversation_id;
  useEffect(() => {
    if (!loaded || (count === 0 && !echoId)) return; // the welcome card reads from the top
    if (query) return; // a filtered thread is read where the reader is
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
  }, [loaded, count, lastState, lastSteps, echoId, conversationId, query]);

  function jumpToLatest() {
    stick.current = true;
    setUnseen(false);
    autoUntil.current = Date.now() + 1500;
    scrollToEnd("smooth");
  }

  /** A different thread reads from its own end, with nothing folded open. */
  function resetThread() {
    setExpanded({});
    setStepsOpen({});
    setUnseen(false);
    setQuery("");
    setSearchOpen(false);
    stick.current = true;
    firstScroll.current = true;
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
    if (query) {
      setQuery("");
      setSearchOpen(false);
    }
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

  /** Stop the reply being worked on; the worker ends it at its next step. */
  async function stop() {
    const id = latest?.state === "processing" ? latest.id : echo?.id;
    if (!id || stopping) return;
    setStopping(true);
    try {
      await api(`/v2/assistant/messages/${encodeURIComponent(id)}/stop`, "POST");
      await load();
      schedule(POLL_BUSY);
    } catch (e) {
      setStopping(false);
      notify((e as Error).message, true);
    }
  }

  async function newChat() {
    if (working) {
      notify("Wait for this reply, or stop it, before starting a new chat.", true);
      return;
    }
    try {
      adopt(await api<AssistantOverview>("/v2/assistant/conversations", "POST"));
      resetThread();
      setHistoryOpen(false);
      boxRef.current?.focus();
    } catch (e) {
      notify((e as Error).message, true);
    }
  }

  async function openChat(id: string) {
    if (id === overview?.conversation_id) {
      setHistoryOpen(false);
      return;
    }
    try {
      adopt(await api<AssistantOverview>(`/v2/assistant/conversations/${encodeURIComponent(id)}`, "PUT"));
      resetThread();
      setHistoryOpen(false);
    } catch (e) {
      notify((e as Error).message, true);
    }
  }

  async function deleteChat(c: AssistantConversation) {
    try {
      adopt(await api<AssistantOverview>(`/v2/assistant/conversations/${encodeURIComponent(c.id)}`, "DELETE"));
      setConfirmDelete(null);
      if (c.current) resetThread();
      notify("Chat deleted. The jobs, resumes and profile changes it made are still in the workspace.");
    } catch (e) {
      notify((e as Error).message, true);
    }
  }

  async function clearHistory() {
    try {
      adopt(await api<AssistantOverview>("/v2/assistant/conversations", "DELETE"));
      setConfirmClear(false);
      setHistoryOpen(false);
      resetThread();
      notify("Chat history cleared. The jobs, resumes and profile changes those chats made are still in the workspace.");
      boxRef.current?.focus();
    } catch (e) {
      notify((e as Error).message, true);
    }
  }

  function exportChat() {
    if (!messages.length) return;
    const title = currentConversation?.title || "Assistant chat";
    const stamp = new Date().toISOString().slice(0, 10);
    const name = "assistant-" + (title.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 40) || "chat") + "-" + stamp + ".md";
    const blob = new Blob([exportMarkdown(title, messages)], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = name;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    notify("Saved " + name + " to your downloads.");
  }

  function toggleSearch(open = !searchOpen) {
    setSearchOpen(open);
    if (!open) setQuery("");
    else window.setTimeout(() => searchRef.current?.focus(), 0);
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
        box.scrollIntoView({ block: "nearest" });
      }, 0);
    }
  }

  async function toggleAutoApply(enabled: boolean) {
    try {
      const next = await api<AssistantOverview>("/v2/assistant/auto-apply", "PUT", { enabled });
      adopt(next);
      notify(
        enabled
          ? "Auto-apply on: changes run without asking first. Each one is still listed in the chat, marked auto-applied."
          : "Auto-apply off: every change asks for your yes first.",
      );
    } catch (e) {
      notify((e as Error).message, true);
    }
  }

  async function chooseEngine(value: string) {
    const [provider, model] = value.split("::");
    try {
      await api("/v2/ai/main", "PUT", { provider, model });
      const fresh = await load();
      notify("Everything now runs on " + (fresh?.engine.options.find((o) => o.provider === provider && o.model === model)?.label || model));
    } catch (e) {
      notify((e as Error).message, true);
    }
  }

  function grow(el: HTMLTextAreaElement) {
    el.style.height = "";
    el.style.height = Math.min(el.scrollHeight, 260) + "px";
  }

  // Keyboard: Esc closes what is open, ⌘⇧O starts a chat, ⌘K searches, "/" jumps to the box.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const cmd = e.metaKey || e.ctrlKey;
      const key = e.key.toLowerCase();
      if (cmd && e.shiftKey && key === "o") {
        e.preventDefault();
        void newChat();
      } else if (cmd && !e.shiftKey && key === "k") {
        e.preventDefault();
        toggleSearch();
      } else if (e.key === "Escape") {
        if (confirmDelete || confirmClear) return; // the dialog closes itself
        if (historyOpen) setHistoryOpen(false);
        else if (railOpen) setRailOpen(false);
        else if (searchOpen) toggleSearch(false);
      } else if (e.key === "/" && !cmd && !e.altKey) {
        const t = e.target as HTMLElement | null;
        if (t && !/^(input|textarea|select)$/i.test(t.tagName) && !t.isContentEditable) {
          e.preventDefault();
          boxRef.current?.focus();
        }
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  const jobs = new Map(data.jobs.map((j) => [j.id, j]));
  const runningNow = data.runs.filter((r) => active(r.state)).length;
  const current = latest?.state === "processing" ? latest.steps[latest.steps.length - 1] : undefined;
  const startedAt = echo ? new Date(echo.at).getTime() : latest?.state === "processing" ? new Date(latest.created_at).getTime() : 0;
  const quick = quickReplies(overview?.pending ?? null);
  const names = new Map(overview?.agents.map((a) => [a.id, AGENT_UI[a.id]?.short || a.name]));
  const conversations = overview?.conversations || [];
  const currentConversation = conversations.find((c) => c.current);
  const q = query.trim();
  const shown = q ? messages.filter((m) => matches(m, q)) : messages;
  const empty = messages.length === 0 && !echo;
  const heading = currentConversation?.title || (empty ? "New chat" : "Assistant");
  return (
    <div className="chat chat-with-rail">
      <div className="chat-main">
        <div className="chat-bar">
          <div className="chat-bar-title">
            <span className="chat-bar-icon" aria-hidden="true">
              <Sparkles size={17} />
            </span>
            <div className="chat-bar-text">
              <h1>Assistant</h1>
              <small title={heading}>
                {heading}
                {messages.length > 0 && <span className="chat-bar-count"> · {messages.length} {messages.length === 1 ? "exchange" : "exchanges"}</span>}
              </small>
            </div>
          </div>
          <div className="chat-bar-actions" role="toolbar" aria-label="Chat actions">
            <button type="button" className="bar-button" onClick={() => void newChat()} title={`New chat (${mod}⇧O)`}>
              <SquarePen size={15} />
              <span>New chat</span>
            </button>
            <button
              type="button"
              className={"bar-button" + (historyOpen ? " on" : "")}
              onClick={() => setHistoryOpen(true)}
              title="Earlier chats"
              aria-haspopup="dialog"
              aria-expanded={historyOpen}
            >
              <History size={15} />
              <span>History</span>
              {conversations.length > 1 && <em className="bar-count">{conversations.length}</em>}
            </button>
            <button
              type="button"
              className={"bar-button" + (searchOpen ? " on" : "")}
              onClick={() => toggleSearch()}
              title={`Search this chat (${mod}K)`}
              aria-pressed={searchOpen}
              disabled={empty}
            >
              <Search size={15} />
              <span>Search</span>
            </button>
            <button type="button" className="bar-button" onClick={exportChat} title="Download this chat as a Markdown file" disabled={empty}>
              <Download size={15} />
              <span>Export</span>
            </button>
            <button
              type="button"
              className="bar-button chat-rail-toggle"
              onClick={() => setRailOpen(true)}
              aria-label="Show the agents"
              title="The agents linked to this chat"
            >
              <Workflow size={15} />
              <span>Agents</span>
              {(working || runningNow > 0) && <span className="rail-live" aria-label="working" />}
            </button>
          </div>
        </div>
        {overview && !overview.ai_configured && (
          <div className="chat-notice" role="status">
            <Badge tone="amber">No AI runtime</Badge>
            <span>Shortcuts only. Install Claude Code or the ChatGPT app, or add a provider key in Settings, and the chat can do the rest.</span>
          </div>
        )}
        {searchOpen && (
          <div className="chat-search" role="search">
            <Search size={15} aria-hidden="true" />
            <input
              ref={searchRef}
              type="search"
              value={query}
              placeholder="Search this chat…"
              aria-label="Search this chat"
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Escape") {
                  e.preventDefault();
                  toggleSearch(false);
                }
              }}
            />
            <small>{q ? `${shown.length} of ${messages.length}` : `${messages.length} ${messages.length === 1 ? "exchange" : "exchanges"}`}</small>
            <button type="button" className="icon-button" aria-label="Close search" onClick={() => toggleSearch(false)}>
              <X size={16} />
            </button>
          </div>
        )}
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
          ) : empty ? (
            <section className="chat-welcome">
              <span className="chat-welcome-icon" aria-hidden="true">
                <Sparkles size={22} />
              </span>
              <h2>{greeting()}. What would you like done?</h2>
              <p>
                Paste a posting and get the one-page PDF back, or ask for anything in plain words. The agent uses the same
                tools the tabs use, asks before anything hard to undo, and never submits for you.
              </p>
              <div className="chat-starters">
                {STARTERS.map((s) => {
                  const Icon = s.icon;
                  return (
                    <button
                      key={s.label}
                      type="button"
                      className="chat-starter"
                      onClick={() =>
                        s.label === "Paste a posting" ? boxRef.current?.focus() : send(s.send || s.label)
                      }
                    >
                      <span className="chat-starter-icon" aria-hidden="true">
                        <Icon size={16} />
                      </span>
                      <b>{s.label}</b>
                      <span>{s.hint}</span>
                    </button>
                  );
                })}
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
          ) : q && shown.length === 0 ? (
            <p className="muted chat-empty-search">Nothing in this chat mentions “{q}”.</p>
          ) : (
            shown.map((m, i) => {
              const day = dayLabel(m.created_at);
              const before = i > 0 ? dayLabel(shown[i - 1].created_at) : "";
              return (
                <Fragment key={m.id}>
                  {day && day !== before && (
                    <div className="chat-day" role="separator">
                      <span>{day}</span>
                    </div>
                  )}
                  <Exchange
                    message={m}
                    names={names}
                    expanded={!!expanded[m.id]}
                    onExpand={() => setExpanded({ ...expanded, [m.id]: !expanded[m.id] })}
                    stepsOpen={stepsOpen[m.id]}
                    onSteps={(open) => setStepsOpen({ ...stepsOpen, [m.id]: open })}
                    onJob={onJob}
                    onSend={send}
                    onEdit={prompt}
                    now={now}
                    jobTier={m.data.job_id ? jobs.get(m.data.job_id)?.sponsor_tier : undefined}
                    stopping={stopping && m.state === "processing"}
                  />
                </Fragment>
              );
            })
          )}
          {echo && !q && (
            <>
              {(!latest || dayLabel(latest.created_at) !== "Today") && (
                <div className="chat-day" role="separator">
                  <span>Today</span>
                </div>
              )}
              <div className="chat-turn you echo">
                <div className="chat-turn-body">
                  <div className="chat-msg you">
                    <div className="chat-text">{echo.text.length > FOLD_AT ? echo.text.slice(0, FOLD_AT) + "…" : echo.text}</div>
                  </div>
                  <div className="chat-meta">
                    <span>Sending…</span>
                  </div>
                </div>
              </div>
              <div className="chat-turn assistant">
                <span className="chat-avatar" aria-hidden="true">
                  <Sparkles size={14} />
                </span>
                <div className="chat-turn-body">
                  <div className="chat-msg assistant processing" aria-busy="true">
                    <Typing label={stopping ? "Stopping…" : "Working on it"} />
                  </div>
                </div>
              </div>
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
          {(unseen || away) && !empty && (
            <button type="button" className={"chat-jump" + (unseen ? " new" : "")} onClick={jumpToLatest} aria-label="Jump to the latest message">
              <ArrowDown size={15} />
              {unseen && <span>New activity</span>}
            </button>
          )}
          {working ? (
            <div className="chat-working" role="status">
              <span className="rail-live" aria-hidden="true" />
              <span className="chat-working-label">
                {stopping ? "Stopping after the current step" : current ? current.label : "Working on it"}
                {!stopping && current?.agent && current.agent !== "assistant" && (
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
                    {quick.map((qr) => (
                      <button key={qr.send} type="button" className={"chip" + (qr.send === "yes" ? " yes" : "")} onClick={() => send(qr.send)}>
                        {qr.send === "yes" && <CheckCircle2 size={13} />}
                        {qr.label}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )
          )}
          <div className={"chat-input" + (working ? " working" : "")}>
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
                } else if (e.key === "Escape" && draft && !e.nativeEvent.isComposing) {
                  e.stopPropagation();
                  setDraft("");
                  grow(e.currentTarget);
                }
              }}
            />
            <div className="chat-input-buttons">
              {working && (
                <button
                  type="button"
                  className="chat-stop"
                  onClick={() => void stop()}
                  disabled={stopping}
                  aria-label={stopping ? "Stopping" : "Stop the reply"}
                  title={stopping ? "Stopping after the current step" : "Stop the reply"}
                >
                  {stopping ? <LoaderCircle className="spin" size={16} /> : <Square size={14} fill="currentColor" />}
                </button>
              )}
              <button className="chat-send" disabled={sending || !draft.trim()} aria-label="Send" title={touch ? "Send" : "Send (Enter)"}>
                {sending ? <LoaderCircle className="spin" size={18} /> : <Send size={17} />}
              </button>
            </div>
          </div>
          <div className="chat-hint">
            {draft.length > 1000 ? (
              <small className="muted">{draft.length.toLocaleString()} characters · a whole posting is fine</small>
            ) : touch ? (
              <small className="muted">Long pastes are fine</small>
            ) : (
              <small className="muted">
                <kbd>Enter</kbd> sends · <kbd>Shift</kbd>+<kbd>Enter</kbd> new line · <kbd>{mod}⇧O</kbd> new chat · <kbd>{mod}K</kbd> search
              </small>
            )}
            <label
              className="chat-auto-toggle"
              title="When on, changes like marking a job applied run without the yes/no question. Every change is still listed in the chat, marked auto-applied."
            >
              <input
                type="checkbox"
                checked={!!overview?.auto_apply}
                onChange={(e) => void toggleAutoApply(e.target.checked)}
              />
              Auto-apply changes
            </label>
          </div>
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
      <HistoryDrawer
        conversations={conversations}
        open={historyOpen}
        onClose={() => setHistoryOpen(false)}
        onOpen={(id) => void openChat(id)}
        onNew={() => void newChat()}
        onDelete={(c) => setConfirmDelete(c)}
        onClear={() => setConfirmClear(true)}
        working={working}
      />
      {confirmDelete && (
        <Modal title="Delete this chat?" onClose={() => setConfirmDelete(null)}>
          <p>
            <b>{confirmDelete.title}</b> — {confirmDelete.count} {confirmDelete.count === 1 ? "exchange" : "exchanges"}, last active{" "}
            {dayLabel(confirmDelete.updated_at).toLowerCase()} at {clock(confirmDelete.updated_at)}.
          </p>
          <p>
            Only the messages go. The jobs, resumes and profile changes this chat made stay in the workspace. This cannot be undone.
          </p>
          <div className="actions">
            <button type="button" className="danger" onClick={() => void deleteChat(confirmDelete)}>
              <Trash2 size={15} /> Delete chat
            </button>
            <button type="button" className="secondary" onClick={() => setConfirmDelete(null)}>
              Keep it
            </button>
          </div>
        </Modal>
      )}
      {confirmClear && (
        <Modal title="Clear all chat history?" onClose={() => setConfirmClear(false)}>
          <p>
            This deletes {conversations.length === 1 ? "the one chat" : `all ${conversations.length} chats`} —{" "}
            {conversations.reduce((n, c) => n + c.count, 0).toLocaleString()} exchanges in total — and opens a fresh one.
          </p>
          <p>
            Only the messages go. The jobs, resumes and profile changes those chats made stay in the workspace. This cannot be undone.
          </p>
          <div className="actions">
            <button type="button" className="danger" onClick={() => void clearHistory()}>
              <Trash2 size={15} /> Clear chat history
            </button>
            <button type="button" className="secondary" onClick={() => setConfirmClear(false)}>
              Keep everything
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
}

/** Three dots while a reply is being worked on, with what is happening right now. */
function Typing({ label }: { label?: string }) {
  return (
    <p className="chat-typing" role="status">
      <span className="chat-dots" aria-hidden="true">
        <i />
        <i />
        <i />
      </span>
      {label && <span>{label}</span>}
    </p>
  );
}

/** Copies to the clipboard and says so for a moment. */
function CopyButton({ text, label }: { text: string; label: string }) {
  const [done, setDone] = useState(false);
  return (
    <button
      type="button"
      className={"chat-tool" + (done ? " done" : "")}
      title={done ? "Copied" : label}
      aria-label={done ? "Copied" : label}
      onClick={async () => {
        if (await copyText(text)) {
          setDone(true);
          window.setTimeout(() => setDone(false), 1600);
        }
      }}
    >
      {done ? <Check size={14} /> : <Copy size={14} />}
      {done && <span>Copied</span>}
    </button>
  );
}

export function HistoryDrawer({
  conversations,
  open,
  onClose,
  onOpen,
  onNew,
  onDelete,
  onClear,
  working = false,
}: {
  conversations: AssistantConversation[];
  open: boolean;
  onClose: () => void;
  onOpen: (id: string) => void;
  onNew: () => void;
  onDelete: (c: AssistantConversation) => void;
  /** Clear every chat at once; asks first. */
  onClear?: () => void;
  /** A reply in progress: nothing can be cleared until it ends. */
  working?: boolean;
}) {
  const groups = useMemo(() => {
    const out: { day: string; items: AssistantConversation[] }[] = [];
    for (const c of conversations) {
      const day = dayLabel(c.updated_at) || "Earlier";
      const last = out[out.length - 1];
      if (last && last.day === day) last.items.push(c);
      else out.push({ day, items: [c] });
    }
    return out;
  }, [conversations]);
  return (
    <>
      {open && <div className="rail-backdrop history-backdrop" onClick={onClose} aria-hidden="true" />}
      <div className={"chat-history" + (open ? " open" : "")} role="dialog" aria-label="Earlier chats" aria-hidden={!open}>
        <div className="rail-head">
          <div>
            <div className="eyebrow">HISTORY</div>
            <h2>Your chats</h2>
          </div>
          <button type="button" className="icon-button" aria-label="Close" onClick={onClose} tabIndex={open ? 0 : -1}>
            <X size={20} />
          </button>
        </div>
        <button type="button" className="secondary history-new" onClick={onNew} tabIndex={open ? 0 : -1}>
          <SquarePen size={15} /> New chat
        </button>
        {conversations.length === 0 ? (
          <p className="muted rail-empty">Nothing yet. The first message starts a chat; every chat stays here until you delete it.</p>
        ) : (
          <div className="history-list">
            {groups.map((g) => (
              <section key={g.day}>
                <div className="rail-label">{g.day}</div>
                <ul>
                  {g.items.map((c) => (
                    <li key={c.id} className={"history-item" + (c.current ? " current" : "")}>
                      <button type="button" className="history-open" onClick={() => onOpen(c.id)} aria-current={c.current ? "true" : undefined} tabIndex={open ? 0 : -1}>
                        <b>{c.title}</b>
                        <small>
                          {c.busy ? "Working… · " : ""}
                          {c.count} {c.count === 1 ? "exchange" : "exchanges"} · {clock(c.updated_at)}
                          {c.current ? " · open now" : ""}
                        </small>
                      </button>
                      <button
                        type="button"
                        className="chat-tool history-delete"
                        aria-label={"Delete " + c.title}
                        title="Delete this chat"
                        onClick={() => onDelete(c)}
                        disabled={c.busy}
                        tabIndex={open ? 0 : -1}
                      >
                        <Trash2 size={14} />
                      </button>
                    </li>
                  ))}
                </ul>
              </section>
            ))}
          </div>
        )}
        <div className="history-foot">
          {onClear && conversations.length > 0 && (
            <button
              type="button"
              className="history-clear"
              onClick={onClear}
              disabled={working}
              title={working ? "Wait for the reply, or stop it, before clearing" : "Delete every chat"}
              tabIndex={open ? 0 : -1}
            >
              <Trash2 size={15} /> Clear chat history
            </button>
          )}
          <p className="muted history-note">Deleting a chat removes only its messages. Jobs, resumes and profile changes stay where they are.</p>
        </div>
      </div>
    </>
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
          {engine.last_fallback && (
            <small className="rail-warn">
              A call on {engine.last_fallback.from_provider} failed and was finished by {engine.last_fallback.to_provider}.
              Set or change the backup in Settings.
            </small>
          )}
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
  onEdit,
  now,
  jobTier,
  stopping = false,
}: {
  message: AssistantMessage;
  names: Map<string, string>;
  expanded: boolean;
  onExpand: () => void;
  stepsOpen?: boolean;
  onSteps: (open: boolean) => void;
  onJob: (id: string) => void;
  onSend: (text: string) => void;
  /** Puts the text back in the composer to change and send again. */
  onEdit?: (text: string) => void;
  now: number;
  jobTier?: string | null;
  stopping?: boolean;
}) {
  const long = m.message.length > FOLD_AT;
  const shown = long && !expanded ? m.message.slice(0, FOLD_AT) + "…" : m.message;
  const working = m.state === "processing";
  const failed = m.state === "failed";
  const stopped = failed && m.data.intent === "stopped";
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
  const currentStep = working ? m.steps[m.steps.length - 1] : undefined;
  return (
    <>
      <div className="chat-turn you">
        <div className="chat-turn-body">
          <div className="chat-msg you">
            <div className="chat-text">{shown}</div>
            {long && (
              <button type="button" className="text-button" onClick={onExpand}>
                {expanded ? "Show less" : `Show all ${m.message.length.toLocaleString()} characters`}
              </button>
            )}
          </div>
          <div className="chat-meta">
            <span className="chat-tools">
              <CopyButton text={m.message} label="Copy your message" />
              {onEdit && (
                <button type="button" className="chat-tool" title="Edit and send again" aria-label="Edit and send again" onClick={() => onEdit(m.message)}>
                  <Pencil size={14} />
                </button>
              )}
            </span>
            <span className="chat-when">{clock(m.created_at)}</span>
          </div>
        </div>
      </div>
      <div className={"chat-turn assistant " + m.state}>
        <span className="chat-avatar" aria-hidden="true">
          <Sparkles size={14} />
        </span>
        <div className="chat-turn-body">
          <div className={"chat-msg assistant " + m.state + (stopped ? " stopped" : "")} aria-busy={working}>
            {m.steps.length > 0 && (
              <div className="chat-steps-wrap">
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
              </div>
            )}
            {working ? (
              <Typing label={stopping ? "Stopping after the current step…" : currentStep ? currentStep.label : "Working on it"} />
            ) : (
              <RichText text={m.response} />
            )}
            {failed && !working && (
              <div className="chat-retry">
                <button type="button" className="secondary" onClick={() => onSend(m.message)}>
                  <RotateCcw size={14} /> {stopped ? "Send it again" : "Try again"}
                </button>
              </div>
            )}
            {m.data.intent === "confirm_tool" && !!m.data.diff?.length && !working && (
              <div className="chat-diff" role="group" aria-label="What will change">
                <b>What changes if you say yes</b>
                {m.data.diff.map((row, i) => (
                  <div key={i} className="chat-diff-row">
                    <span className="chat-diff-field">{row.field}</span>
                    <span className="chat-diff-before">{row.before}</span>
                    <span aria-hidden="true">→</span>
                    <span className="chat-diff-after">{row.after}</span>
                  </div>
                ))}
              </div>
            )}
            {!!m.data.trace?.length && !working && (
              <details className="chat-trace">
                <summary>What I did · {m.data.trace.length} {m.data.trace.length === 1 ? "action" : "actions"}</summary>
                <ol>
                  {m.data.trace.map((t, i) => (
                    <li key={i} className={t.error ? "failed" : ""}>
                      <b>{t.tool.replaceAll("_", " ")}</b>
                      {t.auto_applied && <em className="chat-auto">auto-applied</em>}
                      {t.summary && <small>{t.summary}</small>}
                    </li>
                  ))}
                </ol>
              </details>
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
          </div>
          {!working && (
            <div className="chat-meta">
              <span className="chat-when">
                {stopped ? "Stopped" : failed ? "Failed" : "Answered"} at {clock(m.updated_at)}
              </span>
              <span className="chat-tools">
                <CopyButton text={m.response} label="Copy the reply" />
                <button type="button" className="chat-tool" title="Ask again" aria-label="Ask again" onClick={() => onSend(m.message)}>
                  <RefreshCw size={14} />
                </button>
              </span>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
