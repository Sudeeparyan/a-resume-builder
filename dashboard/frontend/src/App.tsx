import { useEffect, useState } from "react";
import { api, type Health } from "./lib/api";
import { applyTheme, getTheme, type Theme } from "./lib/theme";
import JobHunter from "./tabs/JobHunter";
import ResumeBuilder from "./tabs/ResumeBuilder";
import Profile from "./tabs/Profile";
import SettingsDialog from "./components/SettingsDialog";
import { FolderIcon, GearIcon, MoonIcon, SearchIcon, SunIcon, UserIcon } from "./components/Icons";

export default function App() {
  const [tab, setTab] = useState<"jobs" | "resumes" | "profile">("jobs");
  const [health, setHealth] = useState<Health | null>(null);
  const [showSettings, setShowSettings] = useState(false);
  const [pickedFolder, setPickedFolder] = useState<string | null>(null);
  const [theme, setTheme] = useState<Theme>(getTheme());

  const refresh = () => api.health().then(setHealth).catch(() => setHealth(null));
  useEffect(() => {
    refresh();
  }, []);

  const toggleTheme = () => {
    const next: Theme = theme === "light" ? "dark" : "light";
    setTheme(next);
    applyTheme(next);
  };

  const llm = health?.llm;

  return (
    <div className="app">
      <div className="topbar">
        <span className="brand">
          <span className="mark">CO</span>
          <span>
            Career Ops
            <span className="sub">Find the job, then build the resume for it</span>
          </span>
        </span>

        <div className="tabs">
          <button className={`tab ${tab === "jobs" ? "active" : ""}`} onClick={() => setTab("jobs")}>
            <SearchIcon size={14} /> Job Hunter
          </button>
          <button
            className={`tab ${tab === "resumes" ? "active" : ""}`}
            onClick={() => setTab("resumes")}
          >
            <FolderIcon size={14} /> Resume Builder
          </button>
          <button
            className={`tab ${tab === "profile" ? "active" : ""}`}
            onClick={() => setTab("profile")}
          >
            <UserIcon size={14} /> Profile
          </button>
        </div>

        <div className="spacer" />

        {health && (
          <>
            <span
              className={`pill ${llm?.available ? "good" : "warn"}`}
              title={llm?.available ? `Using ${llm.provider}` : llm?.degraded_note}
            >
              {llm?.available ? `AI on · ${llm.provider}` : "AI off"}
            </span>
            <span
              className={`pill ${health.engine.available ? "" : "bad"}`}
              title={health.engine.note || "The engine that builds your PDF"}
            >
              {health.engine.available ? "PDF ready" : "No PDF engine"}
            </span>
            <span className="pill" title="Employers with H-1B filings on record">
              {health.sponsor_index.rows.toLocaleString()} sponsors
            </span>
          </>
        )}

        <button
          className="themebtn"
          onClick={toggleTheme}
          title={theme === "light" ? "Switch to dark" : "Switch to light"}
        >
          {theme === "light" ? <MoonIcon size={14} /> : <SunIcon size={14} />}
        </button>
        <button className="themebtn" onClick={() => setShowSettings(true)}>
          <GearIcon size={14} /> Settings
        </button>
      </div>

      <div className="body">
        {tab === "jobs" && (
          <JobHunter
            health={health}
            onBuildResume={(folder) => {
              setPickedFolder(folder);
              setTab("resumes");
            }}
          />
        )}
        {tab === "resumes" && <ResumeBuilder health={health} initialFolder={pickedFolder} />}
        {tab === "profile" && <Profile />}
      </div>

      {showSettings && (
        <SettingsDialog
          onClose={() => {
            setShowSettings(false);
            refresh();
          }}
        />
      )}
    </div>
  );
}
