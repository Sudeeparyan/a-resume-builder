/**
 * Her facts — the only thing a resume is allowed to draw from.
 *
 * Two views over the same markdown file. Read shows it laid out properly, so
 * she can check what the system actually believes about her. Edit is the raw
 * text, because these files are hand-written prose and a form would flatten
 * the nuance they carry (the alternative framings of one job, the notes about
 * what is still unsettled).
 *
 * Everything saves through the one sanctioned writer into context/.
 */
import { useEffect, useMemo, useRef, useState } from "react";
import { api, type ProfileFile } from "../lib/api";
import Markdown from "../components/Markdown";
import { Chip } from "../components/ui";

const PRETTY: Record<string, string> = {
  "01-basics.md": "Basics",
  "02-education.md": "Education",
  "03-experience.md": "Experience",
  "04-projects.md": "Projects",
  "05-skills.md": "Skills",
  "06-achievements.md": "Achievements",
  "07-preferences.md": "What you want",
  "08-voice.md": "Voice & tone",
  "09-anything-else.md": "Anything else",
  "QUESTIONS-FOR-YOU.md": "Open questions",
};

export default function Profile() {
  const [files, setFiles] = useState<ProfileFile[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [mode, setMode] = useState<"read" | "edit">("read");
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState<string | null>(null);
  const [err, setErr] = useState("");
  const [profile, setProfile] = useState<any>(null);
  const timer = useRef<number | null>(null);

  const load = () => {
    api
      .profileFiles()
      .then((r) => {
        setFiles(r);
        setSelected((cur) => cur ?? r[0]?.name ?? null);
        setDraft((cur) => (cur ? cur : r[0]?.content ?? ""));
      })
      .catch((e) => setErr(e.message));
    api.profile().then(setProfile).catch(() => {});
  };

  useEffect(() => {
    load();
    return () => {
      if (timer.current) window.clearTimeout(timer.current);
    };
  }, []);

  const pick = (name: string) => {
    if (dirty && selected) {
      if (!window.confirm("You have unsaved changes here. Discard them and switch?")) return;
    }
    setSelected(name);
    setDraft(files.find((x) => x.name === name)?.content ?? "");
    setDirty(false);
    setSavedAt(null);
    setMode("read");
  };

  const save = async () => {
    if (!selected) return;
    setSaving(true);
    setErr("");
    try {
      const r = await api.saveProfileFile(selected, draft);
      setDirty(false);
      setSavedAt(r.saved_at);
      setFiles((prev) =>
        prev.map((f) =>
          f.name === selected ? { ...f, content: draft, chars: draft.length } : f,
        ),
      );
      api.profile().then(setProfile).catch(() => {});
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setSaving(false);
    }
  };

  const active = files.find((f) => f.name === selected);
  const openQuestions: any[] = profile?.open_questions ?? [];

  const skills = useMemo(
    () => ({
      strong: profile?.skills?.strong ?? [],
      used: profile?.skills?.used_it ?? [],
      touched: profile?.skills?.touched_it ?? [],
      gaps: profile?.skills?.honest_gaps ?? [],
    }),
    [profile],
  );

  return (
    <div className="profile">
      <div className="pane">
        <div className="paneheader">
          <strong>Your information</strong>
        </div>

        {openQuestions.length > 0 && (
          <div className="banner warn small" style={{ margin: 9 }}>
            {openQuestions.length} open question{openQuestions.length === 1 ? "" : "s"}.
            Answering the blocking ones unlocks specific claims — like a total
            years-of-experience figure.
          </div>
        )}

        <div className="scroll">
          {files.map((f) => (
            <div
              key={f.name}
              className={`profilelist-item ${selected === f.name ? "selected" : ""}`}
              onClick={() => pick(f.name)}
            >
              <div className="name">{PRETTY[f.name] || f.name}</div>
              <div className="desc">{f.description}</div>
              <div className="small muted" style={{ marginTop: 4 }}>
                {f.chars.toLocaleString()} characters
              </div>
            </div>
          ))}
        </div>
      </div>

      {!active ? (
        <div className="empty">Loading your files…</div>
      ) : (
        <div className="profile-editor-wrap">
          <div className="paneheader">
            <strong>{PRETTY[active.name] || active.name}</strong>
            <span className="small muted mono">{active.name}</span>
            {dirty && <span className="pill warn">unsaved</span>}
            {!dirty && savedAt && <span className="pill good">saved</span>}
            <div className="spacer" />
            <div className="segmented">
              <button className={mode === "read" ? "on" : ""} onClick={() => setMode("read")}>
                Read
              </button>
              <button className={mode === "edit" ? "on" : ""} onClick={() => setMode("edit")}>
                Edit
              </button>
            </div>
            <button className="primary small" onClick={save} disabled={!dirty || saving}>
              {saving ? <span className="spin" /> : "Save"}
            </button>
          </div>

          {err && (
            <div className="banner bad" style={{ margin: "10px 12px 0" }}>
              {err}
            </div>
          )}

          {mode === "read" ? (
            <div className="scroll" style={{ padding: "14px 20px 30px" }}>
              <div className="banner info small">
                {active.description} Everything here is private to you, and it is the
                only thing a resume is allowed to draw from.
              </div>

              {active.name === "05-skills.md" && profile && (
                <div className="panel" style={{ marginBottom: 14 }}>
                  <h3 style={{ marginTop: 0 }}>How each of these can be used</h3>
                  {[
                    ["strong", "Can carry a bullet", skills.strong, "strong"],
                    ["used", "Can carry a bullet", skills.used, "used"],
                    ["touched", "Skills list only — never a bullet", skills.touched, "touched"],
                    ["gaps", "Never appears, in any form", skills.gaps, "gap"],
                  ].map(([key, rule, items, kind]: any) =>
                    items.length ? (
                      <div key={key} style={{ marginBottom: 10 }}>
                        <div className="small muted" style={{ marginBottom: 5 }}>
                          {rule}
                        </div>
                        <div className="chipwrap">
                          {items.slice(0, 40).map((s: string) => (
                            <Chip key={s} kind={kind}>
                              {s}
                            </Chip>
                          ))}
                        </div>
                      </div>
                    ) : null,
                  )}
                </div>
              )}

              {/* Preview what she is editing, not what was last saved --
                  otherwise flipping to Read after a change silently hides it. */}
              <Markdown text={draft || active.content} />
            </div>
          ) : (
            <textarea
              value={draft}
              onChange={(e) => {
                setDraft(e.target.value);
                setDirty(true);
              }}
              spellCheck={false}
              placeholder="Nothing written here yet."
            />
          )}
        </div>
      )}
    </div>
  );
}
