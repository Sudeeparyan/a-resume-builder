/**
 * Talking to the resume.
 *
 * Each reply shows what was actually done and what was refused. A refusal is
 * not an error to hide -- it is usually the most useful thing on the screen,
 * because it names the gap between what she wants to say and what she can
 * honestly claim.
 */
import { useEffect, useRef, useState } from "react";
import { api, type ChatMessage, type ChatTurn } from "../lib/api";

export default function ResumeChat({
  folder,
  disabled,
  onResult,
}: {
  folder: string;
  disabled?: boolean;
  onResult: (t: ChatTurn) => void;
}) {
  const [turns, setTurns] = useState<ChatMessage[]>([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const endRef = useRef<HTMLDivElement | null>(null);

  const load = () => {
    api
      .chatHistory(folder)
      .then((r) => setTurns(r.turns))
      .catch(() => setTurns([]));
  };

  useEffect(() => {
    setErr("");
    load();
  }, [folder]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [turns.length, busy]);

  const send = async () => {
    const msg = text.trim();
    if (!msg || busy) return;
    setText("");
    setBusy(true);
    setErr("");
    // Show her message immediately; the real row arrives with the reload.
    setTurns((t) => [
      ...t,
      {
        id: -1, seq: -1, role: "user", content: msg,
        plan: [], refusals: [], can_undo: false, at: "",
      },
    ]);
    try {
      const res = await api.chat(folder, msg);
      onResult(res);
      load();
    } catch (e: any) {
      setErr(e.message);
      load();
    } finally {
      setBusy(false);
    }
  };

  const undo = async (turnId: number) => {
    setBusy(true);
    try {
      const res = await api.undoTurn(folder, turnId);
      onResult(res as any);
      load();
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", flex: 1, overflow: "hidden" }}>
      <div className="chatlog">
        {turns.length === 0 && (
          <div className="bubble sys">
            Tell me what to change. Try “make it two pages”, “lead with projects”,
            or “add my MiGa project”. I only ever use what is in your Profile.
          </div>
        )}

        {turns.map((t, i) => (
          <div key={`${t.id}-${i}`} className={`bubble ${t.role === "user" ? "user" : "ai"}`}>
            {t.content}

            {t.plan?.filter((p) => p.label).map((p, n) => (
              <div className="planrow" key={n}>
                <span className={p.applied ? "ok" : "no"}>{p.applied ? "✓" : "✕"}</span>
                <span className={p.applied ? "" : "no"}>{p.label}</span>
              </div>
            ))}

            {t.refusals?.map((r, n) => (
              <div className="refusal" key={n}>
                {r.reason}
                {r.what_would_make_it_true && (
                  <div className="fix">{r.what_would_make_it_true}</div>
                )}
              </div>
            ))}

            {t.role === "assistant" && t.can_undo && (
              <div style={{ marginTop: 7 }}>
                <button className="ghost small" onClick={() => undo(t.id)} disabled={busy}>
                  Undo this
                </button>
              </div>
            )}
          </div>
        ))}

        {busy && (
          <div className="bubble ai">
            <span className="spin" />
          </div>
        )}
        <div ref={endRef} />
      </div>

      {err && (
        <div className="banner bad small" style={{ margin: "0 12px 8px" }}>
          {err}
        </div>
      )}

      <div className="composer">
        <textarea
          value={text}
          rows={2}
          disabled={disabled || busy}
          placeholder={disabled ? "Pick a resume first" : "What should I change?"}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send();
            }
          }}
        />
        <button className="primary" onClick={send} disabled={disabled || busy || !text.trim()}>
          Send
        </button>
      </div>
    </div>
  );
}
