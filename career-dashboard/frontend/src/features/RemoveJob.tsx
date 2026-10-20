import { useState } from "react";
import { Modal } from "../components/UI";
import type { Job } from "../types";

/**
 * Why a saved role is removed. The labels match REMOVAL_REASONS in
 * backend/services/reapply.py: the next automatic searches learn from them.
 */
export const REMOVAL_REASONS = [
  { id: "role", label: "Wrong kind of role", learns: "Searches skip this job title at every company from now on." },
  { id: "company", label: "Not this company", learns: "Searches skip every role at this company from now on." },
  {
    id: "sponsor",
    label: "This company won't sponsor me",
    learns: "Searches skip every role at this company from now on.",
  },
  { id: "senior", label: "Too senior for me", learns: "Only this role is skipped from now on." },
  { id: "location", label: "Wrong location", learns: "Only this role is skipped from now on." },
  { id: "other", label: "Not suitable", learns: "Only this role is skipped from now on." },
] as const;

export type RemovalReason = (typeof REMOVAL_REASONS)[number]["id"];

/** The removal reason sent to the API: the chosen label, then her own words. */
export function removalText(reason: RemovalReason, note: string) {
  const label = REMOVAL_REASONS.find((r) => r.id === reason)!.label;
  const extra = note.trim();
  return extra ? `${label}: ${extra}` : label;
}

export function RemoveJobDialog({
  job,
  onCancel,
  onConfirm,
}: {
  job: Job;
  onCancel: () => void;
  onConfirm: (reason: string) => void | Promise<void>;
}) {
  const [reason, setReason] = useState<RemovalReason>("other");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const chosen = REMOVAL_REASONS.find((r) => r.id === reason)!;
  return (
    <Modal title={`Remove ${job.company} · ${job.title}?`} onClose={onCancel}>
      <p>It leaves your active list; its history and files are kept and you can restore it. Why is it not for you?</p>
      <div className="removal-reasons" role="group" aria-label="Why remove it">
        {REMOVAL_REASONS.map((r) => (
          <button
            type="button"
            key={r.id}
            className={"chip" + (r.id === reason ? " selected" : "")}
            aria-pressed={r.id === reason}
            onClick={() => setReason(r.id)}
          >
            {r.label}
          </button>
        ))}
      </div>
      <p className="muted">{chosen.learns}</p>
      <label className="field">
        <span>Anything to add (optional)</span>
        <input value={note} maxLength={300} onChange={(e) => setNote(e.target.value)} />
      </label>
      <div className="actions">
        <button className="secondary" onClick={onCancel}>
          Keep it
        </button>
        <button
          className="danger"
          disabled={busy}
          onClick={async () => {
            setBusy(true);
            try {
              await onConfirm(removalText(reason, note));
            } finally {
              setBusy(false);
            }
          }}
        >
          {busy ? "Removing…" : "Remove role"}
        </button>
      </div>
    </Modal>
  );
}
