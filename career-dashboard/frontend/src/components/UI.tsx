import { useEffect, useRef, useContext, createContext } from "react";
import type { ReactNode } from "react";
import { X, LoaderCircle, ExternalLink, CheckCircle2 } from "lucide-react";
import { safeUrl } from "../api";
import type { Report, Run } from "../types";
export const NoticeContext = createContext<{
  text: string;
  error: boolean;
} | null>(null);
export function Badge({
  children,
  tone = "neutral",
  title,
}: {
  children: ReactNode;
  tone?: string;
  title?: string;
}) {
  return (
    <span className={"badge " + tone} title={title}>
      {children}
    </span>
  );
}
export function Empty({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <div className="empty">
      <h3>{title}</h3>
      <p>{children}</p>
    </div>
  );
}
export function Modal({
  title,
  children,
  onClose,
  wide = false,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
  wide?: boolean;
}) {
  const notice = useContext(NoticeContext);
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    ref.current?.showModal();
    return () => ref.current?.close();
  }, []);
  return (
    <dialog ref={ref} className={wide ? "wide" : ""} onCancel={onClose}>
      <div className="modal-head">
        <h2>{title}</h2>
        <button className="icon-button" aria-label="Close" onClick={onClose}>
          <X size={21} />
        </button>
      </div>
      <div className="modal-body">
        {children}
        {notice && (
          <div
            className={"modal-notice " + (notice.error ? "error" : "")}
            role={notice.error ? "alert" : "status"}
          >
            {notice.text}
          </div>
        )}
      </div>
    </dialog>
  );
}
export function Field({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
    </label>
  );
}
export function Running({ run }: { run: Run }) {
  return (
    <div className={"run-state " + (run.state === "failed" ? "error" : "")}>
      <span>
        {["queued", "running"].includes(run.state) ? (
          <LoaderCircle className="spin" size={18} />
        ) : (
          <CheckCircle2 size={18} />
        )}
      </span>
      <div>
        <b>
          {({research: "Company & hiring review", resume_advisor: "Resume advisor", email: "Gmail sync", discovery: "Job discovery", resume_build: "Resume build & score", resume_match: "Independent document review", instruction_interpret: "Instruction interpreter"} as Record<string, string>)[run.kind] || run.kind}{" "}
          · {run.state}
        </b>
        <small>{run.error || run.result?.stage || "Waiting to start"}</small>
        {!!run.result?.balanced_shortages?.length && (
          <ul className="run-shortages">
            {run.result.balanced_shortages.map((shortage: string) => (
              <li key={shortage}>{shortage}</li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
// Render agent output with React text nodes; never inject HTML.
function Inline({ text }: { text: string }) {
  return (
    <>
      {text
        .split(/(\[[^\]]+\]\(https?:\/\/[^\s)]+\)|\*\*[^*]+\*\*|\*[^*\n]+\*)/g)
        .map((part, n) => {
          const link = part.match(/^\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)$/);
          return link ? (
            <a key={n} href={safeUrl(link[2])} target="_blank" rel="noreferrer">
              {link[1]}
            </a>
          ) : part.startsWith("**") ? (
            <strong key={n}>{part.slice(2, -2)}</strong>
          ) : part.startsWith("*") && part.length > 2 ? (
            <em key={n}>{part.slice(1, -1)}</em>
          ) : (
            part
          );
        })}
    </>
  );
}
export function RichText({ text }: { text: string }) {
  const lines = text.split("\n");
  const blocks: ReactNode[] = [];
  const cells = (line: string) =>
    line
      .trim()
      .replace(/^\||\|$/g, "")
      .split("|")
      .map((c) => c.trim());
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (
      line.trim().startsWith("|") &&
      /^\s*\|?[\s:|\-]+\|?\s*$/.test(lines[i + 1] || "") &&
      (lines[i + 1] || "").includes("---")
    ) {
      const headings = cells(line);
      const rows: string[][] = [];
      const key = i;
      i += 2;
      while (i < lines.length && lines[i].trim().startsWith("|")) {
        rows.push(cells(lines[i]));
        i++;
      }
      i--;
      blocks.push(
        <div className="report-table" key={key}>
          <table>
            <thead>
              <tr>
                {headings.map((h, n) => (
                  <th key={n}>
                    <Inline text={h} />
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r, n) => (
                <tr key={n}>
                  {headings.map((_, c) => (
                    <td key={c}>
                      <Inline text={r[c] || ""} />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>,
      );
    } else if (/^\s*[-•]\s+/.test(line)) {
      // Consecutive "- item" lines become one list.
      const items: string[] = [];
      const key = i;
      while (i < lines.length && /^\s*[-•]\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\s*[-•]\s+/, ""));
        i++;
      }
      i--;
      blocks.push(
        <ul key={key}>
          {items.map((item, n) => (
            <li key={n}>
              <Inline text={item} />
            </li>
          ))}
        </ul>,
      );
    } else if (line.startsWith("### "))
      blocks.push(<h4 key={i}>{line.slice(4)}</h4>);
    else if (line.startsWith("## "))
      blocks.push(<h3 key={i}>{line.slice(3)}</h3>);
    else if (line.startsWith("# "))
      blocks.push(<h2 key={i}>{line.slice(2)}</h2>);
    else
      blocks.push(
        <p key={i}>
          <Inline text={line} />
        </p>,
      );
  }
  return <div className="report-text">{blocks}</div>;
}
export function ReportView({ report }: { report: Report }) {
  return (
    <>
      <p className="report-summary">{report.summary}</p>
      <RichText text={report.report} />
      {report.limitations.length > 0 && (
        <div className="callout">
          <b>Limits & open questions</b>
          <ul>
            {report.limitations.map((l, i) => (
              <li key={i}>{l}</li>
            ))}
          </ul>
        </div>
      )}
      <div className="source-list">
        {report.sources.map((s, i) => (
          <a key={i} href={safeUrl(s.url)} target="_blank" rel="noreferrer">
            <ExternalLink size={14} />
            {s.title}
            <small>{s.accessed_at}</small>
          </a>
        ))}
      </div>
    </>
  );
}
