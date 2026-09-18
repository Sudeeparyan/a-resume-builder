/**
 * Paste back what Claude or ChatGPT found.
 *
 * She works in a project on her phone, on her subscription, with no API key.
 * This is how that answer becomes tracked, ranked and buildable here -- and
 * why the preview is blunt about what it does not trust: the gates are re-run
 * locally, and a link an assistant produced is not a link anyone has checked.
 */
import { useState } from "react";
import { api, type IngestPreview } from "../lib/api";

export default function IngestDialog({
  onClose,
  onSaved,
}: {
  onClose: () => void;
  onSaved: () => void;
}) {
  const [text, setText] = useState("");
  const [origin, setOrigin] = useState("claude-project");
  const [preview, setPreview] = useState<IngestPreview | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [done, setDone] = useState("");

  const look = async () => {
    setBusy(true);
    setErr("");
    setPreview(null);
    try {
      setPreview(await api.ingestPreview(text, origin));
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  };

  const save = async () => {
    setBusy(true);
    setErr("");
    try {
      const res = await api.ingestSave(text, origin);
      setDone(res.message);
      onSaved();
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="backdrop" onClick={onClose}>
      <div className="modal wide" onClick={(e) => e.stopPropagation()}>
        <h2>Bring in jobs from Claude or ChatGPT</h2>
        <p className="small muted" style={{ marginTop: -4 }}>
          Paste the whole answer — the table or the <code>careerops</code> block. I
          will re-run the sponsorship check and your never-apply-twice list here,
          because an assistant can get both wrong.
        </p>

        {done ? (
          <>
            <div className="banner good">{done}</div>
            <button className="primary" onClick={onClose}>
              Done
            </button>
          </>
        ) : (
          <>
            <div className="field">
              <label>Where did this come from?</label>
              <select value={origin} onChange={(e) => setOrigin(e.target.value)}>
                <option value="claude-project">Claude project</option>
                <option value="chatgpt-project">ChatGPT project</option>
                <option value="pasted">Somewhere else</option>
              </select>
            </div>

            <div className="field">
              <label>The answer</label>
              <textarea
                rows={9}
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="Paste the assistant's reply here…"
                spellCheck={false}
                style={{ fontFamily: "var(--mono)", fontSize: "var(--fs-2)" }}
              />
            </div>

            {err && <div className="banner bad">{err}</div>}

            {preview && (
              <>
                <div className="banner info small">
                  Found <strong>{preview.found}</strong> job
                  {preview.found === 1 ? "" : "s"}.{" "}
                  <strong>{preview.jobs.length}</strong> would be kept
                  {preview.excluded.length > 0 && (
                    <>
                      , <strong>{preview.excluded.length}</strong> ruled out
                    </>
                  )}
                  {preview.duplicates > 0 && <> · {preview.duplicates} duplicate(s)</>}.
                </div>

                {preview.warnings.map((w, i) => (
                  <div className="banner warn small" key={i}>
                    {w}
                  </div>
                ))}

                {preview.jobs.length > 0 && (
                  <div className="overflow-x" style={{ maxHeight: 240, overflowY: "auto" }}>
                    <table>
                      <thead>
                        <tr>
                          <th>Company</th>
                          <th>Role</th>
                          <th>Tier</th>
                          <th>Ad text</th>
                          <th>Link</th>
                        </tr>
                      </thead>
                      <tbody>
                        {preview.jobs.map((j, i) => (
                          <tr key={i}>
                            <td>{j.company}</td>
                            <td>{j.role_title}</td>
                            <td>
                              <span className={`tier ${j.tier}`} title={j.tier_why}>
                                {j.tier}
                              </span>
                            </td>
                            <td className={j.has_ad_text ? "" : "muted"}>
                              {j.has_ad_text ? "yes" : "missing"}
                            </td>
                            <td className="muted">{j.url ? "unverified" : "none"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                {preview.excluded.length > 0 && (
                  <>
                    <h3>Ruled out</h3>
                    <div className="overflow-x" style={{ maxHeight: 180, overflowY: "auto" }}>
                      <table>
                        <tbody>
                          {preview.excluded.map((e, i) => (
                            <tr key={i}>
                              <td>{e.company}</td>
                              <td>{e.why}</td>
                              <td className="muted">
                                {e.triggering_sentence ? `“${e.triggering_sentence}”` : ""}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </>
                )}
              </>
            )}

            <div style={{ display: "flex", gap: 8, marginTop: 16 }}>
              <button onClick={look} disabled={!text.trim() || busy}>
                {busy && !preview ? <span className="spin" /> : "Look at it first"}
              </button>
              <button
                className="primary"
                onClick={save}
                disabled={!preview || preview.jobs.length === 0 || busy}
              >
                {preview ? `Import ${preview.jobs.length} job(s)` : "Import"}
              </button>
              <div className="spacer" />
              <button className="ghost" onClick={onClose}>
                Cancel
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
