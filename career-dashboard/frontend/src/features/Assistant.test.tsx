import { describe, it, expect } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { clock, dayLabel, elapsed, exportMarkdown, flowFor, matches, quickReplies, Exchange, HistoryDrawer } from "./Assistant";
import { RichText } from "../components/UI";
import type { AssistantConversation, AssistantMessage, Run } from "../types";

const message = (steps: AssistantMessage["steps"], state: AssistantMessage["state"] = "done"): AssistantMessage => ({
  id: "m1", message: "x", response: "y", state, steps, data: {}, created_at: "", updated_at: "",
});
const step = (agent: string, state: "running" | "done" | "failed", detail = "", run_id?: string) => ({
  at: "", label: agent, state, detail, agent, run_id,
});

describe("Agent rail flow", () => {
  it("shows the posting pipeline before the first message", () => {
    const { nodes, live } = flowFor(undefined, []);
    expect(nodes.map((n) => n.id)).toEqual(["assistant", "sponsorship", "resume", "resume_match"]);
    expect(live).toBe(false);
    expect(nodes.every((n) => n.state === "idle")).toBe(true);
  });
  it("collapses the real steps into one node per agent, in order, and keeps a running one lit", () => {
    const { nodes, live } = flowFor(
      message([step("assistant", "done", "Read"), step("sponsorship", "done", "Tier B"), step("resume", "done", "v1"), step("resume", "running", "Fitting")], "processing"),
      [],
    );
    expect(nodes.map((n) => [n.id, n.state])).toEqual([["assistant", "done"], ["sponsorship", "done"], ["resume", "running"]]);
    expect(nodes[2].detail).toBe("Fitting");
    expect(live).toBe(true);
  });
  it("follows a background run the chat started until it finishes", () => {
    const runs: Run[] = [{ id: "r1", kind: "study_plan", job_id: "j", state: "running", result: { stage: "Drafting the plan" }, error: null, created_at: "", updated_at: "" }];
    const started = flowFor(message([step("study_plan", "done", "queued", "r1")]), runs);
    expect(started.nodes[0].state).toBe("running");
    expect(started.nodes[0].detail).toBe("Study plan · Drafting the plan");
    expect(started.live).toBe(true);
    const finished = flowFor(message([step("study_plan", "done", "queued", "r1")]), [{ ...runs[0], state: "completed" }]);
    expect(finished.nodes[0].state).toBe("done");
    expect(finished.live).toBe(false);
    const failed = flowFor(message([step("study_plan", "done", "queued", "r1")]), [{ ...runs[0], state: "failed", error: "No provider" }]);
    expect(failed.nodes[0]).toMatchObject({ state: "failed", detail: "No provider" });
  });
});

describe("Composer helpers", () => {
  it("offers one-tap answers only for questions that take them", () => {
    expect(quickReplies(null)).toEqual([]);
    expect(quickReplies({ kind: "confirm_tool" }).map((q) => q.send)).toEqual(["yes", "no"]);
    expect(quickReplies({ kind: "confirm_applied" })[0].label).toBe("Yes, go ahead");
    expect(quickReplies({ kind: "posting_link" })).toEqual([]);
    expect(quickReplies({ kind: "agent" })).toEqual([]);
    const pick = quickReplies({ kind: "choose_job", candidates: [{ id: "a", company: "Acme", title: "Data Engineer" }, { id: "b", company: "Beta", title: "Analyst" }] });
    expect(pick).toEqual([{ label: "1. Acme — Data Engineer", send: "1" }, { label: "2. Beta — Analyst", send: "2" }]);
  });
  it("formats how long an exchange took", () => {
    expect(elapsed(0.4)).toBe("0 s");
    expect(elapsed(41.6)).toBe("42 s");
    expect(elapsed(65)).toBe("1 m 05 s");
    expect(elapsed(-3)).toBe("0 s");
    expect(clock("not a date")).toBe("");
    expect(clock("2026-09-19T18:30:24+00:00")).toMatch(/\d/);
  });
});

describe("Thread helpers", () => {
  const today = new Date(2026, 8, 19, 15, 0, 0);
  it("labels days relative to today", () => {
    expect(dayLabel(new Date(2026, 8, 19, 8).toISOString(), today)).toBe("Today");
    expect(dayLabel(new Date(2026, 8, 18, 23, 59).toISOString(), today)).toBe("Yesterday");
    expect(dayLabel(new Date(2026, 8, 15, 12).toISOString(), today)).toMatch(/Sep 15/);
    expect(dayLabel(new Date(2025, 11, 31, 12).toISOString(), today)).toMatch(/2025/);
    expect(dayLabel("nope", today)).toBe("");
  });
  it("finds exchanges that mention every search word, on either side", () => {
    const m = { message: "research Snowflake", response: "Snowflake is a cloud data platform in Bozeman." };
    expect(matches(m, "snowflake")).toBe(true);
    expect(matches(m, "bozeman data")).toBe(true);
    expect(matches(m, "databricks")).toBe(false);
    expect(matches(m, "   ")).toBe(true);
  });
  it("exports the conversation as Markdown with both sides and the PDF path", () => {
    const md = exportMarkdown("Snowflake resume", [
      { ...message([]), message: "paste", response: "Saved **Snowflake — Backend**.", created_at: "2026-09-19T10:00:00Z", updated_at: "2026-09-19T10:00:30Z", data: { pdf: "applications/x/resume.pdf" } },
      { ...message([], "failed"), id: "m2", message: "again", response: "Stopped.", created_at: "2026-09-19T10:01:00Z", updated_at: "2026-09-19T10:01:05Z" },
    ], today);
    expect(md.startsWith("# Snowflake resume\n")).toBe(true);
    expect(md).toContain("2 exchanges");
    expect(md).toContain("**You** ·");
    expect(md).toContain("Saved **Snowflake — Backend**.");
    expect(md).toContain("Resume PDF: applications/x/resume.pdf");
    expect(md).toContain("**Assistant** (failed) ·");
  });
});

describe("Rendering", () => {
  const names = new Map([["sponsorship", "Sponsorship gate"]]);
  const base = { names, expanded: false, onExpand() {}, onSteps() {}, onJob() {}, onSend() {}, onEdit() {}, now: Date.now() };
  it("renders a finished exchange with its tools, card and suggestions", () => {
    const html = renderToStaticMarkup(
      <Exchange
        {...base}
        message={{
          ...message([step("sponsorship", "done", "Tier B")]),
          message: "paste of a posting",
          response: "Saved. Here is `code` and\n```\nraw block\n```",
          created_at: "2026-09-19T10:00:00Z",
          updated_at: "2026-09-19T10:00:30Z",
          data: { intent: "resume_ready", pdf: "a/b.pdf", company: "Acme", title: "Engineer", coverage: 72, ats: 95, suggestions: ["open Acme"], job_id: "j1" },
        }}
      />,
    );
    expect(html).toContain("Copy your message");
    expect(html).toContain("Edit and send again");
    expect(html).toContain("Copy the reply");
    expect(html).toContain("Ask again");
    expect(html).toContain("Download PDF");
    expect(html).toContain("open Acme");
    expect(html).toContain("<pre><code>raw block</code></pre>");
    expect(html).toContain("<code>code</code>");
    expect(html).toContain("1 step in 30 s");
  });
  it("shows typing dots while working and a stop note when stopping", () => {
    const working = renderToStaticMarkup(<Exchange {...base} message={message([step("assistant", "running", "")], "processing")} stopping />);
    expect(working).toContain("chat-dots");
    expect(working).toContain("Stopping after the current step");
    expect(working).not.toContain("Copy the reply");
    const stopped = renderToStaticMarkup(<Exchange {...base} message={{ ...message([], "failed"), data: { intent: "stopped" } }} />);
    expect(stopped).toContain("Send it again");
    expect(stopped).toContain("Stopped at");
  });
  it("lists earlier chats grouped by day with the open one marked", () => {
    const now = new Date();
    const conversations: AssistantConversation[] = [
      { id: "a", title: "status", count: 3, started_at: now.toISOString(), updated_at: now.toISOString(), busy: false, current: true },
      { id: "b", title: "Software Engineer, Data Platform", count: 1, started_at: "2026-01-02T10:00:00Z", updated_at: "2026-01-02T10:00:00Z", busy: true, current: false },
    ];
    const html = renderToStaticMarkup(<HistoryDrawer conversations={conversations} open onClose={() => {}} onOpen={() => {}} onNew={() => {}} onDelete={() => {}} onClear={() => {}} />);
    expect(html).toContain("Today");
    expect(html).toContain("Clear chat history");
    const empty = renderToStaticMarkup(<HistoryDrawer conversations={[]} open onClose={() => {}} onOpen={() => {}} onNew={() => {}} onDelete={() => {}} onClear={() => {}} />);
    expect(empty).not.toContain("Clear chat history");
    const busy = renderToStaticMarkup(<HistoryDrawer conversations={conversations} open working onClose={() => {}} onOpen={() => {}} onNew={() => {}} onDelete={() => {}} onClear={() => {}} />);
    expect(busy).toMatch(/history-clear"[^>]*disabled/);
    expect(html).toContain("open now");
    expect(html).toContain("Working… · 1 exchange");
    expect(html).toContain('aria-current="true"');
    expect(html).toContain("Delete Software Engineer, Data Platform");
  });
  it("keeps fenced code verbatim and never as markup", () => {
    const html = renderToStaticMarkup(<RichText text={"```\n<b>not bold</b>\n```"} />);
    expect(html).toContain("&lt;b&gt;not bold&lt;/b&gt;");
    expect(html).not.toContain("<b>not bold</b>");
  });
});
