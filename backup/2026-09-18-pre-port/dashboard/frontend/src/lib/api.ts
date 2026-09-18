/** Everything the UI knows about the backend. */

export type Tier = "S" | "A" | "B" | "C" | "EXCLUDED";

export interface Job {
  id: string;
  source: string;
  company: string;
  role_title: string;
  url: string;
  location: string;
  remote: boolean;
  department: string;
  posted_at: string | null;
  jd_chars: number;
  jd_text?: string;
  tier: Tier;
  tier_label: string;
  verdict: string;
  reason_label: string;
  triggering_sentence: string | null;
  everify: boolean;
  cap_exempt: boolean;
  h1b_approvals: number;
  link_status: string;
  score: number;
  score_detail: {
    skill_match: number;
    competition: number;
    company_profile: number;
    recency: number;
    total: number;
    evidence: Record<string, string>;
  };
  jd: {
    must_haves?: { text: string; keyword: string; under_required_heading?: boolean }[];
    nice_to_haves?: { text: string; keyword: string }[];
    hiring_problem?: string;
    years_required?: number | null;
    source?: string;
  };
  research: {
    what_they_do?: string;
    engineering_reality?: string;
    current_projects?: string[];
    future_direction?: string[];
    team_shape?: string;
    pressures?: string[];
    day_job_months_1_3?: string;
    day_job_month_12?: string;
    demand_map?: DemandRow[];
    fit_narrative?: string;
    questions_to_ask?: string[];
    sources?: string[];
  };
  prediction: {
    must_have?: string[];
    she_has?: string[];
    she_lacks?: string[];
    must_have_coverage?: number;
    probability?: number;
    probability_band?: string;
    rationale?: string;
    lift_if_learned?: { skill: string; new_probability: number; learn_days: number }[];
  };
  recommendation: string;
  ghost_flags: string[];
}

export interface DemandRow {
  skill: string;
  named_by?: string;
  centrality: "core" | "important" | "peripheral";
  candidate_level: "strong" | "used_it" | "touched_it" | "none";
  destination: "resume" | "study_plan" | "honest_gap";
  evidence_url?: string | null;
  note?: string;
}

export interface Excluded {
  company: string;
  role_title: string;
  url: string;
  stage: string;
  why: string;
  triggering_sentence: string | null;
  at: string;
}

export interface Stage {
  key: string;
  label: string;
  status: "PENDING" | "RUNNING" | "DONE" | "SKIPPED" | "FAILED";
  items_total: number;
  items_done: number;
  duration_ms: number;
  note: string;
}

export interface RunState {
  id: string;
  status: string;
  message: string;
  error: string | null;
  stages: Stage[];
  elapsed_seconds: number;
  eta_seconds_p50: number;
  eta_seconds_p80: number;
  eta_human: string;
  cost_usd: number;
  counts: Record<string, number>;
  source_report: { source: string; ok: boolean; count: number; error?: string }[];
  resume_after: string | null;
}

export interface ResumeSummary {
  folder: string;
  company: string;
  role_title: string;
  tier: string;
  score: string;
  status: string;
  app_id: string;
  url: string;
  has_pdf: boolean;
  has_research: boolean;
  has_study_plan: boolean;
  updated_at: string;
}

export interface Violation {
  kind: string;
  severity: "blocker" | "important" | "nice";
  message: string;
  evidence: string;
  block_id: string | null;
  line: number | null;
  token: string | null;
}

export interface CompileResult {
  ok: boolean;
  mode: string;
  pages: number;
  text_chars: number;
  underfilled: boolean;
  pdf_b64: string | null;
  log_tail: string;
  problems: {
    severity: string;
    kind: string;
    line: number | null;
    message: string;
    raw: string;
  }[];
  duration_ms: number;
  cache_hit: boolean;
  guards: {
    ok: boolean;
    blocker_count: number;
    violation_count: number;
    violations: Violation[];
  };
  ats: {
    score: number;
    rows: { term: string; weight: number; count: number; claimable?: boolean }[];
    missing: string[];
  } | null;
  /** Only present on an apply-suggestion response: the file after the edit. */
  tex?: string;
}

export interface ProfileFile {
  name: string;
  description: string;
  content: string;
  chars: number;
  exists: boolean;
}

export interface Health {
  llm: {
    provider: string;
    available: boolean;
    reason: string;
    key_set: boolean;
    key_hint: string;
    key_verified: boolean | null;
    key_message: string;
    cli_available: boolean;
    cli_reason: string;
    web_search: boolean;
    degraded: boolean;
    degraded_note: string;
    models: Record<string, string>;
  };
  engine: { available: boolean; engine: string | null; note: string };
  sponsor_index: { rows: number; current: boolean };
  workspace: { context_files: number; applications_tsv: boolean; output_folders: number };
  sources: Record<string, boolean>;
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || body.error || detail;
    } catch {
      /* keep the status text */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// the hiring manager, the resume chat, the rules box, ingest, the brief
// ---------------------------------------------------------------------------
export interface ManagerVerdict {
  role_in_one_line: string;
  what_breaks_without_this_hire?: string;
  seniority_read?: string;
  mandatory: { requirement: string; why_disqualifying?: string; how_i_check?: string; evidence_quote?: string }[];
  strong_signals: { signal: string; why_it_moves_me?: string; how_rare?: string }[];
  perfect_projects: {
    name: string; what_it_proves?: string; stack?: string[];
    scope?: string; rough_effort_days?: number; what_bad_looks_like?: string;
  }[];
  screening_questions: {
    question: string; what_a_good_answer_contains?: string; what_a_bad_answer_sounds_like?: string;
  }[];
  instant_rejects: { signal: string; why?: string }[];
  the_bar: string;
  degraded_note?: string;
  sources?: string[];
}

export interface ManagerVerdictRow {
  job_id: string;
  company: string;
  role_title: string;
  verdict: ManagerVerdict;
  sources: string[];
  degraded: boolean;
  stale?: boolean;
  created_at: string;
}

export interface ManagerStart {
  cached: boolean;
  run_id?: string;
  status?: string;
  message?: string;
  verdict?: ManagerVerdict;
  sources?: string[];
  degraded?: boolean;
  created_at?: string;
}

export interface PlanOp {
  op: string;
  args: Record<string, any>;
  why?: string;
  label?: string;
  applied: boolean;
}

export interface Refusal {
  request: string;
  reason: string;
  what_would_make_it_true?: string;
}

export interface ChatMessage {
  id: number;
  seq: number;
  role: "user" | "assistant";
  content: string;
  plan: PlanOp[];
  refusals: Refusal[];
  can_undo: boolean;
  at: string;
}

export interface ChatTurn extends Partial<CompileResult> {
  reply: string;
  plan: PlanOp[];
  refusals: Refusal[];
  changed: boolean;
  saved: boolean;
  ship_ok_reset: boolean;
  turn_id: number;
  spec: any;
  pages_target: number;
  tex: string;
  rules: Rule[];
  rules_added?: Rule[];
  cost_usd: number;
}

export interface Rule {
  id: number;
  scope: "folder" | "global";
  folder: string;
  text: string;
  op: string;
  args: Record<string, any>;
  enabled: boolean;
  position: number;
  source: string;
  mechanical: boolean;
  stale?: boolean;
  created_at: string;
}

export interface IngestPreview {
  found: number;
  duplicates: number;
  jobs: {
    company: string; role_title: string; url: string; location: string;
    tier: Tier; tier_why: string; score: number; has_ad_text: boolean;
    ghost_flags: string[]; link_status: string;
  }[];
  excluded: { company: string; role_title: string; why: string; triggering_sentence: string | null; stage: string }[];
  warnings: string[];
}

export interface Schedule {
  enabled: boolean;
  at: string;
  count: number;
  build_resumes: boolean;
  last_run: string;
  next_run: string;
  running_now: boolean;
  last_error: string;
  last_brief?: any;
}

export const api = {
  health: () => req<Health>("/health"),
  settings: () => req<any>("/settings"),
  saveSettings: (body: any) => req<any>("/settings", { method: "PUT", body: JSON.stringify(body) }),
  saveKey: (key: string) =>
    req<{ ok: boolean; message: string; key_set: boolean; key_hint?: string }>("/settings/key", {
      method: "POST",
      body: JSON.stringify({ key }),
    }),
  testKey: () => req<{ ok: boolean; message: string }>("/settings/test-key", { method: "POST" }),

  startRun: (count: number) =>
    req<RunState>("/runs", { method: "POST", body: JSON.stringify({ count }) }),
  getRun: (id: string) => req<RunState>(`/runs/${id}`),
  listRuns: () => req<any[]>("/runs"),
  cancelRun: (id: string) => req<any>(`/runs/${id}/cancel`, { method: "POST" }),

  jobs: (limit = 50) => req<Job[]>(`/jobs?limit=${limit}`),
  job: (id: string) => req<Job>(`/jobs/${encodeURIComponent(id)}`),
  excluded: (limit = 100) => req<Excluded[]>(`/excluded?limit=${limit}`),
  tailor: (jobId: string) =>
    req<{ folder: string; report: any; guards: any; pages: number; message: string }>(
      "/tailor",
      { method: "POST", body: JSON.stringify({ job_id: jobId }) },
    ),

  resumes: () => req<ResumeSummary[]>("/resumes"),
  resume: (folder: string) => req<any>(`/resumes/${encodeURIComponent(folder)}`),
  saveResume: (folder: string, tex: string) =>
    req<any>(`/resumes/${encodeURIComponent(folder)}`, {
      method: "PUT",
      body: JSON.stringify({ tex }),
    }),
  compile: (folder: string, tex: string, mode: "draft" | "ship") =>
    req<CompileResult>(`/resumes/${encodeURIComponent(folder)}/compile`, {
      method: "POST",
      body: JSON.stringify({ tex, mode }),
    }),
  applySuggestion: (
    folder: string,
    body: { action: "add_keyword"; keyword: string } | { action: "remove_block"; block_id: string },
  ) =>
    req<CompileResult>(`/resumes/${encodeURIComponent(folder)}/apply-suggestion`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  profile: () => req<any>("/profile"),
  profileFiles: () => req<ProfileFile[]>("/profile/files"),
  saveProfileFile: (name: string, content: string) =>
    req<{ ok: boolean; saved_at: string; chars: number }>(
      `/profile/files/${encodeURIComponent(name)}`,
      { method: "PUT", body: JSON.stringify({ content }) },
    ),
  tracker: () => req<any>("/tracker"),
  setStatus: (appId: string, status: string, note = "") =>
    req<any>(`/tracker/${appId}/status`, {
      method: "POST",
      body: JSON.stringify({ status, note }),
    }),
  summary: () => req<{ markdown: string }>("/summary"),

  // ---- the hiring manager's bar (never sees her profile) ----
  managerRun: (jobId: string, force = false) =>
    req<ManagerStart>("/manager", {
      method: "POST",
      body: JSON.stringify({ job_id: jobId, force }),
    }),
  manager: (jobId: string) =>
    req<ManagerVerdictRow>(`/manager/${encodeURIComponent(jobId)}`),

  // ---- talking to a resume ----
  chat: (folder: string, message: string, confirmRebuild = false) =>
    req<ChatTurn>(`/resumes/${encodeURIComponent(folder)}/chat`, {
      method: "POST",
      body: JSON.stringify({ message, confirm_rebuild: confirmRebuild }),
    }),
  chatHistory: (folder: string) =>
    req<{ turns: ChatMessage[] }>(`/resumes/${encodeURIComponent(folder)}/chat`),
  clearChat: (folder: string) =>
    req<any>(`/resumes/${encodeURIComponent(folder)}/chat`, { method: "DELETE" }),
  undoTurn: (folder: string, turnId: number) =>
    req<any>(`/resumes/${encodeURIComponent(folder)}/chat/${turnId}/undo`, { method: "POST" }),

  // ---- the rules box ----
  rules: (folder: string) =>
    req<{ folder: Rule[]; global: Rule[]; spec: any }>(
      `/resumes/${encodeURIComponent(folder)}/rules`,
    ),
  addRule: (folder: string, text: string, scope: "folder" | "global" = "folder") =>
    req<Rule>(`/resumes/${encodeURIComponent(folder)}/rules`, {
      method: "POST",
      body: JSON.stringify({ text, scope }),
    }),
  updateRule: (folder: string, id: number, patch: Partial<Rule>) =>
    req<Rule>(`/resumes/${encodeURIComponent(folder)}/rules/${id}`, {
      method: "PATCH",
      body: JSON.stringify(patch),
    }),
  deleteRule: (folder: string, id: number) =>
    req<any>(`/resumes/${encodeURIComponent(folder)}/rules/${id}`, { method: "DELETE" }),
  rebuild: (folder: string) =>
    req<any>(`/resumes/${encodeURIComponent(folder)}/rebuild`, { method: "POST" }),

  // ---- bringing a Claude / ChatGPT answer back in ----
  ingestPreview: (text: string, origin = "pasted") =>
    req<IngestPreview>("/ingest/preview", {
      method: "POST",
      body: JSON.stringify({ text, origin }),
    }),
  ingestSave: (text: string, origin = "pasted") =>
    req<{ saved: number; excluded: number; message: string }>("/ingest/save", {
      method: "POST",
      body: JSON.stringify({ text, origin }),
    }),

  // ---- the morning brief and the portable pack ----
  schedule: () => req<Schedule>("/schedule"),
  saveSchedule: (body: Partial<Schedule>) =>
    req<Schedule>("/schedule", { method: "PUT", body: JSON.stringify(body) }),
  startBrief: (count?: number) =>
    req<any>("/brief", { method: "POST", body: JSON.stringify(count ? { count } : {}) }),
  brief: () => req<{ last: any; running: boolean }>("/brief"),
  buildPack: () =>
    req<{ folder: string; zip: string; files: { name: string; kb: number }[]; message: string }>(
      "/pack",
      { method: "POST" },
    ),
};

/** Live run events. Reconnects with the last sequence number so nothing is missed. */
export function subscribeRun(
  runId: string,
  onEvent: (ev: any) => void,
  afterSeq = 0,
): () => void {
  let seq = afterSeq;
  let closed = false;
  let es: EventSource | null = null;

  const connect = () => {
    if (closed) return;
    es = new EventSource(`/api/runs/${runId}/events?after=${seq}`);
    const handle = (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data);
        if (data.seq) seq = data.seq;
        onEvent(data);
        if (data.type === "run_finished") {
          closed = true;
          es?.close();
        }
      } catch {
        /* ignore a malformed frame */
      }
    };
    for (const t of [
      "run_started", "stage_started", "stage_progress", "stage_finished",
      "log", "eta", "artifact", "run_finished", "error", "quota_wait", "ping",
    ]) {
      es.addEventListener(t, handle as EventListener);
    }
    es.onerror = () => {
      es?.close();
      if (!closed) setTimeout(connect, 1500);
    };
  };

  connect();
  return () => {
    closed = true;
    es?.close();
  };
}
