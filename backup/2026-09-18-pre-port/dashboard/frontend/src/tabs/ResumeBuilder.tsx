/**
 * The resume, as a conversation.
 *
 * She is not a developer, so LaTeX is not the interface -- the PDF is what she
 * looks at, the chat is how she changes it, and the Rules box is how a change
 * sticks. The editor still exists, behind "Edit the LaTeX", for the times she
 * wants to nudge one character by hand.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import {
  api, type ChatTurn, type CompileResult, type Health, type ResumeSummary, type Rule,
} from "../lib/api";
import LatexEditor from "../components/LatexEditor";
import PdfPane from "../components/PdfPane";
import ResumeChat from "../components/ResumeChat";
import RulesBox from "../components/RulesBox";
import { DownloadIcon, FolderIcon } from "../components/Icons";
import { Empty } from "../components/ui";

const DEBOUNCE_MS = 900;

export default function ResumeBuilder({
  health,
  initialFolder,
}: {
  health: Health | null;
  initialFolder: string | null;
}) {
  const [list, setList] = useState<ResumeSummary[]>([]);
  const [folder, setFolder] = useState<string | null>(initialFolder || null);
  const [doc, setDoc] = useState<any>(null);
  const [tex, setTex] = useState("");
  const [result, setResult] = useState<CompileResult | null>(null);
  const [rules, setRules] = useState<Rule[]>([]);
  const [pagesTarget, setPagesTarget] = useState(1);
  const [shipOk, setShipOk] = useState(false);
  const [building, setBuilding] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [err, setErr] = useState("");
  const [zoom, setZoom] = useState(1.25);
  const [showEditor, setShowEditor] = useState(false);
  const timer = useRef<number | null>(null);

  const loadList = () =>
    api.resumes().then((r) => {
      setList(r);
      return r;
    });

  useEffect(() => {
    loadList()
      .then((r) => {
        if (!folder && r.length) setFolder(r[0].folder);
      })
      .catch((e) => setErr(e.message));
    // A pending debounce must not fire into an unmounted tab.
    return () => {
      if (timer.current) window.clearTimeout(timer.current);
    };
  }, []);

  useEffect(() => {
    if (!initialFolder) return;
    loadList()
      .then(() => setFolder(initialFolder))
      .catch((e) => setErr(e.message));
  }, [initialFolder]);

  const refreshRules = useCallback(() => {
    if (!folder) return;
    api
      .rules(folder)
      .then((r) => setRules([...r.global, ...r.folder]))
      .catch(() => {});
  }, [folder]);

  useEffect(() => {
    if (!folder) return;
    // Switching resumes mid-typing must not let the old debounce compile the
    // previous document against the new folder.
    if (timer.current) window.clearTimeout(timer.current);
    setErr("");
    setResult(null);
    api
      .resume(folder)
      .then((d) => {
        setDoc(d);
        setTex(d.tex);
        setRules(d.rules ?? []);
        setPagesTarget(d.pages_target ?? 1);
        setShipOk(!!d.ship_ok);       // server truth, so it survives a reload
        setDirty(false);
        compile(d.tex, "draft");
      })
      .catch((e) => setErr(e.message));
  }, [folder]);

  const compile = useCallback(
    async (source: string, mode: "draft" | "ship") => {
      if (!folder || !source.trim()) return;
      setBuilding(true);
      try {
        const res = await api.compile(folder, source, mode);
        setResult(res);
        if (mode === "ship") setShipOk(res.ok);
        else if (!res.ok) setShipOk(false);
        setErr("");
      } catch (e: any) {
        setErr(e.message);
      } finally {
        setBuilding(false);
      }
    },
    [folder],
  );

  const onChange = (v: string) => {
    setTex(v);
    setDirty(true);
    setShipOk(false);
    if (timer.current) window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => compile(v, "draft"), DEBOUNCE_MS);
  };

  const save = async () => {
    if (!folder) return;
    try {
      await api.saveResume(folder, tex);
      setDirty(false);
      setShipOk(false);
      await compile(tex, "draft");
    } catch (e: any) {
      setErr(e.message);
    }
  };

  const finalise = async () => {
    if (!folder) return;
    if (dirty) await api.saveResume(folder, tex);
    setDirty(false);
    await compile(tex, "ship");
  };

  // A chat turn already saved, guarded and compiled server-side. Take its word
  // for the new state rather than re-fetching and flickering.
  const onChatResult = (t: ChatTurn) => {
    if (t.tex) setTex(t.tex);
    if (t.rules) setRules(t.rules);
    if (typeof t.pages_target === "number") setPagesTarget(t.pages_target);
    if (t.ship_ok_reset) setShipOk(false);
    if (t.pdf_b64 || t.problems) setResult((prev) => ({ ...(prev ?? {}), ...t } as CompileResult));
    setDirty(false);
  };

  const rebuild = async () => {
    if (!folder) return;
    setBuilding(true);
    setErr("");
    try {
      const res = await api.rebuild(folder);
      if (res.tex) setTex(res.tex);
      setShipOk(false);
      setDirty(false);
      await compile(res.tex, "draft");
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBuilding(false);
    }
  };

  const blockers = result?.guards?.violations.filter((v) => v.severity === "blocker") ?? [];
  const errors = result?.problems?.filter((p) => p.severity === "error") ?? [];
  const aiOff = health && !health.llm?.available;

  return (
    <div className={`builder ${folder ? "" : "no-side"}`}>
      {/* ---- which resume ---- */}
      <div className="pane">
        <div className="paneheader">
          <strong>Your resumes</strong>
        </div>
        <div className="scroll">
          {list.length === 0 ? (
            <div className="empty small">
              None yet. Go to Job Hunter, open a job, and press “Build a resume”.
            </div>
          ) : (
            list.map((r) => (
              <div
                key={r.folder}
                className={`resumeitem ${folder === r.folder ? "selected" : ""}`}
                onClick={() => setFolder(r.folder)}
              >
                <div style={{ fontWeight: 600, fontSize: "var(--fs-3)" }}>
                  {r.company || r.folder}
                </div>
                <div className="small muted">{r.role_title || "—"}</div>
                <div style={{ display: "flex", gap: 6, marginTop: 5 }}>
                  {r.tier && <span className={`tier ${r.tier[0]}`}>{r.tier[0]}</span>}
                  {r.has_pdf && <span className="chip">PDF</span>}
                  <span className="chip">{r.status}</span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {!folder ? (
        <Empty icon={<FolderIcon size={30} />} title="Pick a resume on the left">
          You will see the finished page, and you can change it by asking.
        </Empty>
      ) : (
        <>
          {/* ---- the page ---- */}
          <div className="pane">
            <div className="paneheader">
              <strong>
                {doc?.company ? `${doc.company} — ${doc.role_title || ""}` : folder}
              </strong>
              {dirty && <span className="pill warn">unsaved</span>}
              {result && (
                <>
                  <span className={`pill ${result.pages === pagesTarget ? "good" : "bad"}`}>
                    {result.pages} of {pagesTarget} page{pagesTarget === 1 ? "" : "s"}
                  </span>
                  {result.underfilled && (
                    <span className="pill warn" title="A thin page reads as thin experience">
                      thin
                    </span>
                  )}
                  {result.ats && <span className="pill">ATS {result.ats.score}%</span>}
                  <span className={`pill ${blockers.length ? "bad" : "good"}`}>
                    {blockers.length ? `${blockers.length} to fix` : "claims check out"}
                  </span>
                </>
              )}
              <div className="spacer" />
              <button className="ghost small" onClick={() => setZoom((z) => Math.max(0.6, z - 0.15))}>
                −
              </button>
              <button className="ghost small" onClick={() => setZoom((z) => Math.min(2.5, z + 0.15))}>
                +
              </button>
              <button className="ghost small" onClick={() => setShowEditor(true)}>
                Edit the LaTeX
              </button>
            </div>

            {err && <div className="banner bad" style={{ margin: 9 }}>{err}</div>}
            {errors.length > 0 && (
              <div className="banner bad" style={{ margin: 9 }}>
                <strong>Line {errors[0].line ?? "?"}:</strong> {errors[0].message}
              </div>
            )}
            {blockers.length > 0 && (
              <div className="banner warn small" style={{ margin: 9 }}>
                <strong>{blockers[0].message}</strong>
                {blockers.length > 1 && ` (and ${blockers.length - 1} more)`}
              </div>
            )}

            <PdfPane b64={result?.pdf_b64 ?? null} zoom={zoom} />

            <div className="paneheader" style={{ borderTop: "1px solid var(--line)", borderBottom: "none" }}>
              <button className="primary" onClick={finalise} disabled={building}
                      title="Runs every honesty check once more and unlocks the download">
                {building ? <span className="spin" /> : "Check & finish"}
              </button>
              <a
                href={shipOk ? `/api/resumes/${encodeURIComponent(folder)}/pdf` : undefined}
                onClick={(e) => {
                  if (!shipOk) e.preventDefault();
                }}
              >
                <button disabled={!shipOk} title={shipOk ? "" : "Run Check & finish first"}
                        style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                  <DownloadIcon size={14} /> Download
                </button>
              </a>
              <a href={`/api/resumes/${encodeURIComponent(folder)}/tex`}>
                <button className="ghost small">.tex</button>
              </a>
              <div className="spacer" />
              <button className="ghost small" onClick={rebuild} disabled={building}
                      title="Rebuild from your Profile, applying every rule">
                Rebuild
              </button>
            </div>
          </div>

          {/* ---- rules and chat ---- */}
          <div className="pane">
            <RulesBox folder={folder} rules={rules} onChanged={refreshRules} />
            {aiOff && (
              <div className="banner warn small" style={{ margin: 9 }}>
                The chat needs an AI model. You can still edit by hand, and every
                honesty check still runs.
              </div>
            )}
            <ResumeChat folder={folder} disabled={!!aiOff} onResult={onChatResult} />
          </div>
        </>
      )}

      {/* ---- the drawer she never has to open ---- */}
      {showEditor && folder && (
        <>
          <div className="drawer-backdrop" onClick={() => setShowEditor(false)} />
          <div className="drawer">
            <div className="paneheader">
              <strong>The LaTeX behind this resume</strong>
              {dirty && <span className="pill warn">unsaved</span>}
              <div className="spacer" />
              <button className="ghost small" onClick={save} disabled={!dirty}>
                Save
              </button>
              <button className="ghost small" onClick={() => compile(tex, "draft")}>
                {building ? <span className="spin" /> : "Rebuild preview"}
              </button>
              <button className="ghost small" onClick={() => setShowEditor(false)}>
                Close
              </button>
            </div>
            <div className="banner info small" style={{ margin: 10 }}>
              Editing here is fine, but a rebuild from your Profile would overwrite it —
              the chat will warn you before that happens.
            </div>
            <LatexEditor
              value={tex}
              problems={result?.problems ?? []}
              onChange={onChange}
              onSave={save}
              jumpToLine={null}
            />
          </div>
        </>
      )}
    </div>
  );
}
