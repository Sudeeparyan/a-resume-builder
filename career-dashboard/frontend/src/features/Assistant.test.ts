import { describe, it, expect } from "vitest";
import { clock, elapsed, flowFor, quickReplies } from "./Assistant";
import type { AssistantMessage, Run } from "../types";

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
