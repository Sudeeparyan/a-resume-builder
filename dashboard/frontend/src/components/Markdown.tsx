/**
 * A small markdown renderer.
 *
 * The research notes, study plans and profile files are all markdown, and
 * dumping them as preformatted text wastes most of their structure. This
 * handles the subset those files actually use -- headings, lists, tables,
 * bold, italics, inline code, fenced code, quotes and links -- and nothing
 * else, which keeps it a few dozen lines instead of a dependency.
 *
 * It builds React elements rather than setting innerHTML, so nothing in a
 * file can inject markup into the page.
 */
import type { ReactNode } from "react";

function inline(text: string, keyBase: string): ReactNode[] {
  const out: ReactNode[] = [];
  // One pass, longest-first so ** wins over *.
  const re =
    /(\[([^\]]+)\]\(([^)\s]+)\))|(\*\*([^*]+)\*\*)|(`([^`]+)`)|(\*([^*]+)\*)|(_([^_]+)_)/g;
  let last = 0;
  let m: RegExpExecArray | null;
  let i = 0;

  while ((m = re.exec(text)) !== null) {
    if (m.index > last) out.push(text.slice(last, m.index));
    const key = `${keyBase}-i${i++}`;
    if (m[1]) {
      const href = m[3];
      const safe = /^(https?:|mailto:|#|\/)/i.test(href) ? href : "#";
      out.push(
        <a key={key} href={safe} target="_blank" rel="noreferrer">
          {m[2]}
        </a>,
      );
    } else if (m[4]) {
      out.push(<strong key={key}>{m[5]}</strong>);
    } else if (m[6]) {
      out.push(<code key={key}>{m[7]}</code>);
    } else if (m[8]) {
      out.push(<em key={key}>{m[9]}</em>);
    } else if (m[10]) {
      out.push(<em key={key}>{m[11]}</em>);
    }
    last = m.index + m[0].length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

function cells(line: string): string[] {
  return line.trim().replace(/^\||\|$/g, "").split("|").map((c) => c.trim());
}

const isRule = (line: string) =>
  /^\|?[\s:|-]+\|[\s:|-]*$/.test(line.trim()) && line.includes("-");

export default function Markdown({ text }: { text: string }) {
  if (!text || !text.trim()) {
    return <div className="empty small">Nothing here yet.</div>;
  }

  const lines = text.replace(/\r\n/g, "\n").split("\n");
  const blocks: ReactNode[] = [];
  let i = 0;
  let key = 0;

  while (i < lines.length) {
    const line = lines[i];

    if (!line.trim()) {
      i++;
      continue;
    }

    // fenced code
    if (line.trim().startsWith("```")) {
      const buf: string[] = [];
      i++;
      while (i < lines.length && !lines[i].trim().startsWith("```")) buf.push(lines[i++]);
      i++;
      blocks.push(
        <pre key={key++}>
          <code>{buf.join("\n")}</code>
        </pre>,
      );
      continue;
    }

    // heading
    const h = /^(#{1,6})\s+(.*)$/.exec(line);
    if (h) {
      const level = Math.min(3, h[1].length);
      const Tag = (["h1", "h2", "h3"] as const)[level - 1];
      blocks.push(<Tag key={key++}>{inline(h[2], `h${key}`)}</Tag>);
      i++;
      continue;
    }

    // table
    if (line.trim().startsWith("|") && i + 1 < lines.length && isRule(lines[i + 1])) {
      const head = cells(line);
      i += 2;
      const rows: string[][] = [];
      while (i < lines.length && lines[i].trim().startsWith("|")) rows.push(cells(lines[i++]));
      blocks.push(
        <div className="tablewrap" key={key++}>
          <table>
            <thead>
              <tr>
                {head.map((c, n) => (
                  <th key={n}>{inline(c, `th${n}`)}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r, n) => (
                <tr key={n}>
                  {r.map((c, m2) => (
                    <td key={m2}>{inline(c, `td${n}-${m2}`)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>,
      );
      continue;
    }

    // quote
    if (line.trim().startsWith(">")) {
      const buf: string[] = [];
      while (i < lines.length && lines[i].trim().startsWith(">")) {
        buf.push(lines[i++].trim().replace(/^>\s?/, ""));
      }
      blocks.push(<blockquote key={key++}>{inline(buf.join(" "), `q${key}`)}</blockquote>);
      continue;
    }

    // list
    if (/^\s*([-*+]|\d+\.)\s+/.test(line)) {
      const ordered = /^\s*\d+\.\s+/.test(line);
      const items: string[] = [];
      while (i < lines.length && /^\s*([-*+]|\d+\.)\s+/.test(lines[i])) {
        items.push(lines[i++].replace(/^\s*([-*+]|\d+\.)\s+/, ""));
      }
      const kids = items.map((it, n) => <li key={n}>{inline(it, `li${n}`)}</li>);
      blocks.push(ordered ? <ol key={key++}>{kids}</ol> : <ul key={key++}>{kids}</ul>);
      continue;
    }

    // paragraph
    const buf: string[] = [];
    while (
      i < lines.length &&
      lines[i].trim() &&
      !/^(#{1,6})\s/.test(lines[i]) &&
      !lines[i].trim().startsWith("|") &&
      !lines[i].trim().startsWith(">") &&
      !lines[i].trim().startsWith("```") &&
      !/^\s*([-*+]|\d+\.)\s+/.test(lines[i])
    ) {
      buf.push(lines[i++]);
    }
    if (buf.length) {
      blocks.push(<p key={key++}>{inline(buf.join(" "), `p${key}`)}</p>);
    } else {
      i++;
    }
  }

  return <div className="md">{blocks}</div>;
}
