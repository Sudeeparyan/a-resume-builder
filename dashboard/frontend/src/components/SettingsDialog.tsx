import { useEffect, useState } from "react";
import { api } from "../lib/api";

export default function SettingsDialog({ onClose }: { onClose: () => void }) {
  const [s, setS] = useState<any>(null);
  const [key, setKey] = useState("");
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.settings().then(setS);
  }, []);

  const saveKey = async () => {
    setBusy(true);
    setMsg(null);
    try {
      const r = await api.saveKey(key);
      setMsg({ ok: r.ok, text: r.message });
      if (r.ok) {
        setKey("");
        setS(await api.settings());
      }
    } catch (e: any) {
      setMsg({ ok: false, text: e.message });
    } finally {
      setBusy(false);
    }
  };

  const toggle = async (field: string, value: any) => {
    const next = { ...s, sources: { ...s.sources, [field]: value } };
    setS(next);
    await api.saveSettings({ [field]: value });
  };

  if (!s) {
    return (
      <div className="backdrop" onClick={onClose}>
        <div className="modal" onClick={(e) => e.stopPropagation()}>Loading…</div>
      </div>
    );
  }

  return (
    <div className="backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div style={{ display: "flex", alignItems: "center" }}>
          <h2 style={{ flex: 1 }}>Settings</h2>
          <button className="ghost" onClick={onClose}>Close</button>
        </div>

        <h3>Claude API key</h3>
        <p className="small muted" style={{ marginTop: -4 }}>
          Everything works without one — finding jobs, the sponsorship check, link
          checking, keyword scoring and building the PDF. A key adds company research,
          resume tailoring and the interview prediction.
        </p>

        {s.key_set && (
          <div className="banner info">
            A key is saved ({s.key_hint}). Leave the box empty and press Save to remove it.
          </div>
        )}

        <div className="field">
          <label>Paste your key</label>
          <input
            type="password"
            value={key}
            placeholder="sk-ant-..."
            onChange={(e) => setKey(e.target.value)}
            autoComplete="off"
          />
          <div className="hint">
            Stored on this computer only, in dashboard/.env, which is never committed.
            Get one at console.anthropic.com.
          </div>
        </div>

        <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
          <button className="primary" onClick={saveKey} disabled={busy}>
            {busy ? <span className="spin" /> : "Save key"}
          </button>
          <button
            onClick={async () => {
              setBusy(true);
              const r = await api.testKey();
              setMsg({ ok: r.ok, text: r.message });
              setBusy(false);
            }}
            disabled={busy || !s.key_set}
          >
            Test it
          </button>
        </div>

        {msg && (
          <div className={`banner ${msg.ok ? "info" : "bad"}`}>{msg.text}</div>
        )}

        <h3>Where to look for jobs</h3>
        <div className="checkrow">
          <input
            type="checkbox"
            checked={s.sources.enable_ats_boards}
            onChange={(e) => toggle("enable_ats_boards", e.target.checked)}
          />
          <div>
            <div>Company job boards</div>
            <div className="small muted">
              Greenhouse, Lever and Ashby. Free, and freshest — a company's own board
              carries a role days before the aggregators.
            </div>
          </div>
        </div>

        <div className="checkrow">
          <input
            type="checkbox"
            checked={s.sources.enable_feeds}
            onChange={(e) => toggle("enable_feeds", e.target.checked)}
          />
          <div>
            <div>Remote job feeds</div>
            <div className="small muted">Remotive, RemoteOK and Arbeitnow. Free, no signup.</div>
          </div>
        </div>

        <div className="checkrow">
          <input
            type="checkbox"
            checked={s.sources.enable_workspace_import}
            onChange={(e) => toggle("enable_workspace_import", e.target.checked)}
          />
          <div>
            <div>Jobs found in Claude Code</div>
            <div className="small muted">
              Reads anything the /hunt command already saved, so nothing is invisible here.
            </div>
          </div>
        </div>

        <div className="checkrow">
          <input
            type="checkbox"
            checked={s.sources.enable_adzuna}
            onChange={(e) => toggle("enable_adzuna", e.target.checked)}
          />
          <div>
            <div>Adzuna</div>
            <div className="small muted">
              Broad US coverage, 1,000 free searches a month. Needs a free signup.
            </div>
          </div>
        </div>

        {s.sources.enable_adzuna && (
          <>
            <div className="field">
              <label>Adzuna app ID</label>
              <input
                value={s.sources.adzuna_app_id || ""}
                onChange={(e) => setS({ ...s, sources: { ...s.sources, adzuna_app_id: e.target.value } })}
                onBlur={(e) => api.saveSettings({ adzuna_app_id: e.target.value })}
              />
            </div>
            <div className="field">
              <label>Adzuna app key</label>
              <input
                type="password"
                onBlur={(e) => api.saveSettings({ adzuna_app_key: e.target.value })}
              />
            </div>
          </>
        )}

        <div className="checkrow">
          <input
            type="checkbox"
            checked={s.sources.enable_usajobs}
            onChange={(e) => toggle("enable_usajobs", e.target.checked)}
          />
          <div>
            <div>USAJobs (federal)</div>
            <div className="small muted">
              Free. Many federal and federally funded employers are cap-exempt, which
              means no H-1B lottery.
            </div>
          </div>
        </div>

        {s.sources.enable_usajobs && (
          <div className="field">
            <label>Your email (USAJobs asks for one)</label>
            <input
              defaultValue={s.sources.usajobs_email || ""}
              onBlur={(e) => api.saveSettings({ usajobs_email: e.target.value })}
            />
          </div>
        )}

        <h3>Models</h3>
        <p className="small muted">
          Deep work uses {s.models.deep}, reading uses {s.models.mid}, and mechanical
          work uses {s.models.fast}.
        </p>
      </div>
    </div>
  );
}
