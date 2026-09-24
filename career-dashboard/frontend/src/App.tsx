import { Component, useCallback, useEffect, useState } from "react";
import type { ReactNode } from "react";
import {
  LayoutDashboard,
  MessageSquareText,
  Search,
  FileText,
  ShieldCheck,
  UserRound,
  SlidersHorizontal,
  Workflow,
  CheckCircle2,
  LoaderCircle,
  X,
} from "lucide-react";
import { api, PROFILE_ID } from "./api";
import { ProfileContext, ProfileMenu, firstName, openProfile, timeLabel, useProfileListing } from "./profiles";
import Onboarding from "./features/Onboarding";
import OnboardingChat from "./features/OnboardingChat";
import { AskContext, Field, Loading, Modal, NoticeContext } from "./components/UI";
import JobDetail from "./components/JobDetail";
import Dashboard from "./features/Dashboard";
import DailySearch from "./features/DailySearch";
import ResumeStudio from "./features/ResumeStudio";
import Assurance from "./features/Assurance";
import Profile from "./features/Profile";
import Settings from "./features/Settings";
import Agents, { AGENT_LABEL } from "./features/Agents";
import Assistant from "./features/Assistant";
import type { Summary } from "./types";
const tabs = [
  ["assistant", "Assistant", MessageSquareText, "Your search"],
  ["dashboard", "Dashboard", LayoutDashboard, "Your search"],
  ["daily", "Daily Search", Search, "Your search"],
  ["resumes", "Resume Studio", FileText, "Your search"],
  ["assurance", "Assurance", ShieldCheck, "Your search"],
  ["profile", "Profile", UserRound, "You"],
  ["agents", "Agents", Workflow, "Behind the scenes"],
  ["settings", "Settings", SlidersHorizontal, "Behind the scenes"],
] as const;
function routeFromHash() {
  const r = location.hash.slice(1).split("/")[0];
  // The chat is the front door: it opens first unless the address names a tab.
  return tabs.some((t) => t[0] === r) ? r : "assistant";
}

/** A render failure in one page must not unmount the whole app. */
class ErrorBoundary extends Component<
  { children: ReactNode },
  { message: string }
> {
  state = { message: "" };
  static getDerivedStateFromError(error: unknown) {
    return { message: error instanceof Error ? error.message : String(error) };
  }
  componentDidCatch(error: unknown) {
    console.error("Page render failed:", error);
  }
  render() {
    if (!this.state.message) return this.props.children;
    return (
      <div className="callout warning" role="alert">
        Something on this page failed to display ({this.state.message}). Your
        data is safe.
        <button
          className="secondary"
          onClick={() => this.setState({ message: "" })}
        >
          Try again
        </button>
        <button className="secondary" onClick={() => location.reload()}>
          Reload the app
        </button>
      </div>
    );
  }
}
export default function App() {
  // Which profile this tab belongs to (the /p/<id>/ address) and the others on this PC.
  const { listing, current, failed, reload } = useProfileListing();
  const onboarding = current?.state === "onboarding";
  // Profiles are known (or the server predates them): the workspace can load.
  const ready = Boolean(current && !onboarding) || failed;
  useEffect(() => {
    if (!listing) return;
    // "/" or an unknown profile: go to the last-used one, keeping the tab named in the address.
    if (!PROFILE_ID || !listing.profiles.some((p) => p.id === PROFILE_ID))
      openProfile(listing.last_used || "annie", location.hash.slice(1));
  }, [listing]);
  useEffect(() => {
    if (current) document.title = `${firstName(current.name) || current.name} · Career Workspace`;
  }, [current]);
  const [route, setRoute] = useState(routeFromHash);
  const [data, setData] = useState<Summary>();
  const [error, setError] = useState("");
  const [toast, setToast] = useState<{ text: string; error: boolean } | null>(
    null,
  );
  const [selected, setSelected] = useState<string | null>(null);
  const [studioJob, setStudioJob] = useState<string | null>(() =>
    location.hash.startsWith("#resumes/")
      ? decodeURIComponent(location.hash.slice(9))
      : null,
  );
  const [add, setAdd] = useState(false);
  // A new profile is set up in the chat; the form is one click away (remembered per browser).
  const [setupForm, setSetupForm] = useState(() => {
    try {
      return localStorage.getItem("setup-view") === "form";
    } catch {
      return false;
    }
  });
  const chooseSetup = (form: boolean) => {
    setSetupForm(form);
    try {
      localStorage.setItem("setup-view", form ? "form" : "chat");
    } catch {
      /* private window: the choice lasts for this page only */
    }
  };
  // A question another tab handed to the Assistant; `n` makes asking the same thing twice count.
  const [asked, setAsked] = useState<{ text: string; send: boolean; n: number } | null>(null);
  const ask = useCallback((text: string, send = true) => {
    setSelected(null);
    setAsked((prev) => ({ text, send, n: (prev?.n ?? 0) + 1 }));
    location.hash = "assistant";
    setRoute("assistant");
  }, []);
  const notify = useCallback(
    (text: string, error = false) => setToast({ text, error }),
    [],
  );
  const refresh = useCallback(async () => {
    try {
      setData(await api("/v2/summary"));
      setError("");
    } catch (e) {
      setError((e as Error).message);
      throw e;
    }
  }, []);
  useEffect(() => {
    if (!ready) return;
    refresh().catch(() => {});
    const timer = setInterval(() => refresh().catch(() => {}), 8000);
    const hash = () => {
      setRoute(routeFromHash());
      if (location.hash.startsWith("#resumes/"))
        setStudioJob(decodeURIComponent(location.hash.slice(9)));
    };
    window.addEventListener("hashchange", hash);
    return () => {
      clearInterval(timer);
      window.removeEventListener("hashchange", hash);
    };
  }, [refresh, ready]);
  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(null), 10000);
    return () => clearTimeout(timer);
  }, [toast]);
  function navigate(r: string) {
    location.hash =
      r === "resumes" && studioJob
        ? "resumes/" + encodeURIComponent(studioJob)
        : r;
    setRoute(r);
  }
  function openStudio(id: string) {
    setStudioJob(id);
    location.hash = "resumes/" + encodeURIComponent(id);
    setRoute("resumes");
  }
  const job = data?.jobs.find((j) => j.id === selected);
  const working = (data?.runs || []).filter((r) =>
    ["queued", "running"].includes(r.state),
  );
  const workingJob = working[0]
    ? data?.jobs.find((j) => j.id === working[0].job_id)
    : undefined;
  const tab = tabs.find((t) => t[0] === route);
  return (
    <ProfileContext.Provider value={{ current, profiles: listing?.profiles || [], reload }}>
    <NoticeContext.Provider value={toast}>
      <AskContext.Provider value={ask}>
      <div className="app">
        <aside>
          {listing ? (
            <ProfileMenu />
          ) : (
            <div className="brand">
              <b>A</b>
              <div>
                ANNIE<small>CAREER WORKSPACE</small>
              </div>
            </div>
          )}
          <nav aria-label="Main navigation">
            {tabs.map(([id, label, Icon, group], i) => (
              <div key={id} className="nav-item">
                {group !== tabs[i - 1]?.[3] && (
                  <span className="nav-group">{group}</span>
                )}
                <button
                  title={onboarding ? "Available once this profile is built" : label}
                  aria-current={route === id && !onboarding ? "page" : undefined}
                  className={route === id && !onboarding ? "active" : ""}
                  disabled={onboarding}
                  onClick={() => navigate(id)}
                >
                  <Icon size={20} />
                  <span>{label}</span>
                  {id === "agents" && working.length > 0 && (
                    <span className="nav-count" aria-label={`${working.length} working`}>
                      {working.length}
                    </span>
                  )}
                </button>
              </div>
            ))}
          </nav>
          <div className="sidebar-note">
            <span className="status-dot" /> Personal workspace
            <p>
              A little progress.
              <br />
              Every single day.
            </p>
            <small>Saved locally · {timeLabel(current?.market?.timezone)}</small>
          </div>
        </aside>
        <main>
          <header>
            <span className="crumb">
              {onboarding ? (
                <>
                  New profile <span aria-hidden="true">/</span> <b>Add documents</b>
                </>
              ) : (
                <>
                  {tab?.[3]} <span aria-hidden="true">/</span> <b>{tab?.[1]}</b>
                </>
              )}
            </span>
            <span className="header-status">
              <button
                className={"live-pill" + (working.length ? " busy" : "")}
                onClick={() => navigate("agents")}
                title="Open the Agents tab"
              >
                {working.length ? (
                  <>
                    <LoaderCircle className="spin" size={14} />
                    {AGENT_LABEL[working[0].kind] || working[0].kind}
                    {workingJob ? ` · ${workingJob.company}` : ""}
                    {working.length > 1 ? ` +${working.length - 1}` : ""}
                  </>
                ) : (
                  <>
                    <span className={"status-dot" + (error ? " off" : "")} />
                    {error ? "Connection needs attention" : "Agents idle"}
                  </>
                )}
              </button>
              {listing ? <ProfileMenu compact /> : <span className="avatar">AM</span>}
            </span>
          </header>
          <div className="page">
            {onboarding && current ? (
              setupForm ? (
                <Onboarding profile={current} notify={notify} onUseChat={() => chooseSetup(false)} />
              ) : (
                <OnboardingChat profile={current} notify={notify} onUseForm={() => chooseSetup(true)} />
              )
            ) : (
            <>
            {error && (
              <div className="callout warning" role="alert">
                {error}
                <button
                  className="secondary"
                  onClick={() => refresh().catch(() => {})}
                >
                  Retry connection
                </button>
              </div>
            )}
            {!data ? (
              <Loading label="Loading your workspace" />
            ) : (
              <ErrorBoundary>
                {route === "assistant" && (
                  <Assistant
                    data={data}
                    refresh={refresh}
                    notify={notify}
                    onJob={openStudio}
                    asked={asked}
                    onAsked={() => setAsked(null)}
                  />
                )}
                {route === "dashboard" && (
                  <Dashboard
                    data={data}
                    refresh={refresh}
                    notify={notify}
                    onJob={openStudio}
                    onDaily={() => navigate("daily")}
                    onAdd={() => setAdd(true)}
                  />
                )}
                {route === "daily" && (
                  <DailySearch
                    data={data}
                    refresh={refresh}
                    notify={notify}
                    onJob={openStudio}
                    onAdd={() => setAdd(true)}
                  />
                )}
                {route === "resumes" && (
                  <ResumeStudio
                    data={data}
                    jobId={studioJob}
                    onJob={openStudio}
                    onDetails={setSelected}
                    refresh={refresh}
                  />
                )}
                {route === "assurance" && (
                  <Assurance
                    data={data}
                    notify={notify}
                    refresh={refresh}
                    onJob={openStudio}
                  />
                )}
                {route === "settings" && <Settings notify={notify} />}
                {route === "agents" && (
                  <Agents
                    data={data}
                    notify={notify}
                    onJob={openStudio}
                    onSettings={() => navigate("settings")}
                    onAssurance={() => navigate("assurance")}
                  />
                )}
                {route === "profile" && (
                  <Profile refresh={refresh} notify={notify} />
                )}
              </ErrorBoundary>
            )}
            </>
            )}
          </div>
        </main>
        {toast && (
          <div
            role={toast.error ? "alert" : "status"}
            className={"toast " + (toast.error ? "error" : "")}
          >
            <CheckCircle2 size={20} />
            <span>{toast.text}</span>
            <button
              aria-label="Dismiss notification"
              onClick={() => setToast(null)}
            >
              <X size={16} />
            </button>
          </div>
        )}
        {job && data && (
          <JobDetail
            key={job.id}
            job={job}
            data={data}
            onClose={() => setSelected(null)}
            refresh={refresh}
            notify={notify}
          />
        )}
        {add && data && (
          <AddJob
            defaultLocation={
              !current?.market || current.market.code === "us" ? "Remote (US)" : current.market.default_location
            }
            date={data.goals.date}
            onClose={() => setAdd(false)}
            refresh={refresh}
            notify={notify}
            onSelect={openStudio}
          />
        )}
      </div>
      </AskContext.Provider>
    </NoticeContext.Provider>
    </ProfileContext.Provider>
  );
}
function AddJob({
  defaultLocation,
  date,
  onClose,
  refresh,
  notify,
  onSelect,
}: {
  defaultLocation: string;
  date: string;
  onClose: () => void;
  refresh: () => Promise<void>;
  notify: (s: string, e?: boolean) => void;
  onSelect: (s: string) => void;
}) {
  const [form, setForm] = useState({
    company: "",
    title: "",
    location: defaultLocation,
    url: "",
    requisition_id: "",
    description: "",
  });
  const [today, setToday] = useState(true);
  const [busy, setBusy] = useState(false);
  return (
    <Modal title="Save a job posting" onClose={onClose}>
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          try {
            const r = await api("/v2/jobs", "POST", form);
            // The sponsorship gate and the never-re-apply rules run before anything is saved.
            if (r.excluded) {
              await refresh();
              onClose();
              notify(
                `Not saved: the posting says “${r.sentence}”. ${r.reason_label}. It is listed under Excluded roles on the Dashboard, where you can restore it if that is wrong.`,
                true,
              );
              return;
            }
            if (r.blocked) {
              notify("Not saved: " + r.note, true);
              return;
            }
            if (today && !r.duplicate)
              await api("/search-runs/" + date + "/jobs/" + r.job.id, "POST");
            await refresh();
            onClose();
            onSelect(r.job.id);
            // Discovery gates on relevance before saving; a job you add by hand is
            // always saved, but you are told when it scores poorly and why.
            const weak =
              !r.duplicate && r.relevance && r.relevance.eligible === false
                ? ` Fit ${r.relevance.score}/100 — ${(r.relevance.blockers || []).join(" ")}`
                : "";
            notify(
              (r.duplicate
                ? "This posting is already saved. Opening its existing record."
                : r.upgraded
                  ? "Full posting added to the application previously tracked from Gmail."
                  : `Job saved to your workspace (sponsorship tier ${r.job?.sponsor_tier || "C"}).`) + weak,
              !!weak,
            );
          } catch (e) {
            notify((e as Error).message, true);
          } finally {
            setBusy(false);
          }
        }}
      >
        <div className="form-grid">
          {[
            ["company", "Company"],
            ["title", "Job title"],
            ["location", "Location"],
            ["requisition_id", "Requisition ID (optional)"],
          ].map(([key, label]) => (
            <Field key={key} label={label}>
              <input
                required={key !== "requisition_id"}
                maxLength={150}
                value={form[key as keyof typeof form]}
                onChange={(e) => setForm({ ...form, [key]: e.target.value })}
              />
            </Field>
          ))}
        </div>
        <Field label="Direct posting URL">
          <input
            type="url"
            required
            maxLength={2500}
            value={form.url}
            onChange={(e) => setForm({ ...form, url: e.target.value })}
          />
        </Field>
        <Field label="Full job description">
          <textarea
            rows={9}
            required
            minLength={80}
            maxLength={100000}
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
          />
        </Field>
        <label className="check-line">
          <input
            type="checkbox"
            checked={today}
            onChange={(e) => setToday(e.target.checked)}
          />
          Add new posting to today’s search
        </label>
        <button className="primary" disabled={busy}>
          {busy ? "Saving…" : "Save job"}
        </button>
      </form>
    </Modal>
  );
}
