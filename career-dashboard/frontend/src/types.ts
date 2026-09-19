export type Job = {
  id: string;
  company: string;
  title: string;
  location: string;
  url: string;
  description: string;
  status: string;
  notes: string;
  application_date: string | null;
  folder: string | null;
  created_at: string;
  selected_project_id: string | null;
  record_source: "posting" | "gmail" | "posting+gmail";
  deleted_at: string | null;
  deletion_reason: string;
  posting_state?: "active" | "expired" | "needs_review";
  last_verified_at?: string | null;
  legitimacy_state?: "verified" | "needs_review" | "blocked" | null;
  size_category?: "startup" | "mid" | "large" | "unknown" | null;
  sponsorship_state?: string | null;
  sponsor_tier?: SponsorTier | null;
  sponsor_evidence?: SponsorEvidence | null;
  closed_at?: string | null;
};
export type SponsorTier = "S" | "A" | "B" | "C";
export type SponsorEvidence = {
  tier?: SponsorTier | "EXCLUDED";
  label?: string;
  reason?: string;
  sentence?: string;
  cap_exempt?: boolean;
  cap_exempt_reason?: string;
  h1b_found?: boolean;
  h1b_approvals?: number;
  h1b_years?: string[];
  everify?: boolean;
};
export type ExcludedJob = {
  id: string;
  company: string;
  title: string;
  location: string;
  url: string;
  reason: string;
  reason_label: string;
  sentence: string;
  pattern?: string;
  source: string;
  excluded_at: string;
  restored_at?: string | null;
};
export type ApplicationDocuments = {
  job_id: string;
  company: string;
  title: string;
  resumes: { label: string; path: string }[];
  cover_letter: {
    version: number;
    path: string;
    created_at: string;
  } | null;
};
export type CoverLetter = {
  job_id: string;
  company: string;
  title: string;
  version: number;
  content: string;
  path: string;
  created_at: string;
  review_required: boolean;
};
export type Report = {
  summary: string;
  report: string;
  sources: { title: string; url: string; accessed_at: string }[];
  limitations: string[];
};
export type Run = {
  id: string;
  kind: string;
  job_id: string | null;
  state: string;
  result: any;
  error: string | null;
  created_at: string;
  updated_at: string;
  provider?: string | null;
  model?: string | null;
  preset?: string;
};
export type Mail = {
  id: string;
  job_id: string | null;
  company: string;
  role: string;
  kind: string;
  subject: string;
  sender: string;
  received_at: string;
  submission_date: string | null;
  excerpt: string;
  reason: string;
  confidence: string;
  state: string;
};
export type Goals = {
  date: string;
  weekly_target: number;
  current_week_target: number;
  week_completed: number;
  daily_base: number;
  carryover: number;
  ahead: number;
  today_target: number;
  today_completed: number;
  remaining_today: number;
  week_remaining: number;
  schedule: {
    date: string;
    label: string;
    planned: number;
    completed: number;
    today: boolean;
  }[];
  settings: { weekly_target: number; workdays: number[]; start_date: string };
};
export type Agent = {
  id: string;
  name: string;
  reads: string;
  profile_access: boolean;
  does: string;
  implementation: string;
  guide: string;
};
export type Summary = {
  jobs: Job[];
  removed_jobs: Job[];
  expired_jobs: Job[];
  excluded_jobs: ExcludedJob[];
  documents: ApplicationDocuments[];
  goals: Goals;
  mail: {
    connection: {
      connected: boolean;
      email?: string;
      last_synced_at?: string;
      coverage?: string;
      mode?: string;
      status?: string;
      last_attempt_at?: string;
      last_error?: string;
    };
    messages: Mail[];
  };
  runs: Run[];
  agents: Agent[];
  profile_dirty: boolean;
  counts: {
    saved: number;
    applied: number;
    interviews: number;
    offers: number;
    excluded: number;
    ghosted: number;
  };
  activity: { id: number; action: string; occurred_at: string; details: any }[];
};
export type Knowledge = {
  id: string;
  kind: string;
  title: string;
  summary: string;
  data: Record<string, any>;
  source: string;
  revision: number;
  review_state: string;
  deleted: boolean;
};
export type ProfileData = {
  items: Knowledge[];
  removed: number;
  registry: Record<string, any>;
  configuration: Record<string, any>;
  sources: Record<string, string>;
  agents: Agent[];
  profile_dirty: boolean;
  pending: { id: string; kind: string; title: string; deleted: boolean; source: string }[];
  revision: number;
  skills: { name: string; purpose: string; path: string }[];
};
export type AssistantStep = {
  at: string;
  label: string;
  state: "running" | "done" | "failed";
  detail: string;
  agent?: string;
  run_id?: string;
};
export type AssistantMessage = {
  id: string;
  message: string;
  response: string;
  state: "processing" | "done" | "needs_input" | "failed";
  steps: AssistantStep[];
  data: {
    intent?: string;
    job_id?: string | null;
    job_ids?: string[];
    company?: string;
    title?: string;
    tier?: string;
    revision?: number;
    pdf?: string | null;
    preview_png?: string | null;
    posting_url?: string;
    coverage?: number | null;
    ats?: number | null;
    gaps?: string[];
    warnings?: string[];
    suggestions?: string[];
    run_id?: string;
    [key: string]: unknown;
  };
  created_at: string;
  updated_at: string;
};
export type AssistantEngine = {
  provider: string;
  model: string;
  label: string;
  ready: boolean;
  moved_from: string | null;
  /** What the runs the chat starts go through (the Settings main choice). */
  runs: { provider: string; model: string; label: string; ready: boolean };
  note: string | null;
  options: { provider: string; model: string; label: string }[];
};
export type AssistantAgent = {
  id: string;
  name: string;
  does: string;
  implementation: string;
  linked: boolean;
  tools: string[];
};
export type AssistantOverview = {
  messages: AssistantMessage[];
  pending: {
    kind: string;
    question?: string;
    candidates?: { id: string; company: string; title: string }[];
    [key: string]: unknown;
  } | null;
  busy: boolean;
  ai_configured: boolean;
  engine: AssistantEngine;
  agents: AssistantAgent[];
  capabilities: { group: string; labels: string[] }[];
};
