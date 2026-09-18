/**
 * Standing instructions, re-applied on every rebuild.
 *
 * Two kinds live here and the difference is shown, never blurred: an
 * "enforced" rule is folded into how the resume is built and genuinely cannot
 * be forgotten; a "guidance" rule only steers what the agent proposes. Telling
 * her they are the same thing would be the easy lie.
 */
import { useState } from "react";
import { api, type Rule } from "../lib/api";

export default function RulesBox({
  folder,
  rules,
  onChanged,
}: {
  folder: string;
  rules: Rule[];
  onChanged: () => void;
}) {
  const [text, setText] = useState("");
  const [scope, setScope] = useState<"folder" | "global">("folder");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const add = async () => {
    const t = text.trim();
    if (!t) return;
    setBusy(true);
    setErr("");
    try {
      await api.addRule(folder, t, scope);
      setText("");
      onChanged();
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  };

  const toggle = async (r: Rule) => {
    try {
      await api.updateRule(folder, r.id, { enabled: !r.enabled });
      onChanged();
    } catch (e: any) {
      setErr(e.message);
    }
  };

  const remove = async (r: Rule) => {
    try {
      await api.deleteRule(folder, r.id);
      onChanged();
    } catch (e: any) {
      setErr(e.message);
    }
  };

  return (
    <div style={{ borderBottom: "1px solid var(--line)", flexShrink: 0 }}>
      <div className="paneheader" style={{ borderBottom: "none" }}>
        <strong>Rules</strong>
        <span className="small muted">applied every time this is rebuilt</span>
      </div>

      {err && (
        <div className="banner bad small" style={{ margin: "0 12px 8px" }}>
          {err}
        </div>
      )}

      <div className="rulelist" style={{ maxHeight: 190, overflowY: "auto" }}>
        {rules.length === 0 && (
          <div className="small muted" style={{ padding: "0 12px 10px" }}>
            No rules yet. Try “always keep it to one page” — either type it below, or
            just say it in the chat.
          </div>
        )}
        {rules.map((r) => (
          <div className={`rule ${r.enabled ? "" : "off"} ${r.stale ? "stale" : ""}`} key={r.id}>
            <input
              type="checkbox"
              checked={r.enabled}
              onChange={() => toggle(r)}
              style={{ width: "auto", marginTop: 2 }}
              title={r.enabled ? "Applied" : "Paused"}
            />
            <div className="txt">
              <div>{r.text}</div>
              <div className="why">
                {r.mechanical ? "enforced" : "guidance"}
                {r.scope === "global" ? " · every resume" : ""}
                {r.stale && " · no longer matches anything in your profile"}
              </div>
            </div>
            <button className="ghost small" onClick={() => remove(r)} title="Delete this rule">
              ✕
            </button>
          </div>
        ))}
      </div>

      <div style={{ display: "flex", gap: 6, padding: "8px 12px 11px" }}>
        <input
          value={text}
          placeholder="Add a rule…"
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") add();
          }}
          style={{ fontSize: "var(--fs-2)" }}
        />
        <select
          value={scope}
          onChange={(e) => setScope(e.target.value as "folder" | "global")}
          style={{ width: 110, fontSize: "var(--fs-1)" }}
          title="Just this resume, or all of them"
        >
          <option value="folder">this one</option>
          <option value="global">all</option>
        </select>
        <button className="small" onClick={add} disabled={busy || !text.trim()}>
          Add
        </button>
      </div>
    </div>
  );
}
