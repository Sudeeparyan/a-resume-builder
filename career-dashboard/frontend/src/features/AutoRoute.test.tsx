import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import AutoRoute from "./AutoRoute";
import type { RouteEndpoint, RoutePolicy } from "../types";

const endpoint = (provider: string, label: string, extra: Partial<RouteEndpoint> = {}): RouteEndpoint => ({
  provider, label, position: 0, enabled: true, ready: true, paid: false,
  models: { strong: provider + "-runtime", cheap: provider + "-runtime" }, capabilities: ["structured", "web"],
  resting: null, last_ok: null, last_error: null, served_today: 0, paid_block: null,
  usage: { tokens: 0, calls: 0, capacity: 1_000_000, capacity_source: "guess", learned_at: null, percent: 0,
           window_resets: null, resets_text: "" },
  ...extra,
});

describe("Auto's route in Settings", () => {
  const endpoints = [
    endpoint("kimi_cli", "Kimi Code", {
      resting: { until: "2026-10-10T05:40:00Z", until_text: "5:40 PM", reason: "usage limit", kind: "limit" },
    }),
    endpoint("codex", "Codex"),
    endpoint("claude_code", "Claude Code"),
    endpoint("antigravity_cli", "Antigravity", { ready: false }),
    endpoint("azure_openai", "Azure OpenAI", { paid: true, usage: null }),
  ];
  const route: RoutePolicy = {
    order: ["kimi_cli", "codex", "claude_code", "antigravity_cli", "azure_openai"],
    enabled: { kimi_cli: true, codex: true, claude_code: true, antigravity_cli: true, azure_openai: true },
    allow_fallbacks: true,
  };
  const html = renderToStaticMarkup(
    <AutoRoute endpoints={endpoints} route={route} busy="" onSave={() => {}} onWake={() => {}} />,
  );

  it("lists her four plans first and the paid API last", () => {
    const at = (label: string) => html.indexOf(label);
    expect(at("Kimi Code")).toBeLessThan(at("Codex"));
    expect(at("Claude Code")).toBeLessThan(at("Antigravity"));
    expect(at("Antigravity")).toBeLessThan(at("Azure OpenAI"));
    expect(html).toContain("paid per call");
    expect(html).toContain("your plan, no extra cost");
  });

  it("says when a resting plan is tried again, and offers to try it now", () => {
    expect(html).toContain("Resting until 5:40 PM");
    expect(html).toContain("Try now");
    expect(html).toContain("Not set up");
  });
});
