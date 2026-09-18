import { describe, it, expect } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { RichText, ReportView } from "./UI";
import { JobList, TierBadge, tierTitle } from "./JobList";
import { ExcludedRoles } from "../features/Dashboard";
import { safeUrl, fileUrl } from "../api";
import type { Job } from "../types";
describe("Agent report safety", () => {
  it("renders untrusted markup as plain text", () => {
    const html = renderToStaticMarkup(
      <RichText
        text={
          "<script>alert(1)</script>\n[Unsafe](javascript:alert(1))\n[Source](https://example.test/source)"
        }
      />,
    );
    expect(html).not.toContain("<script>");
    expect(html).not.toContain('href="javascript:');
    expect(html).toContain('href="https://example.test/source"');
  });
  it("rejects credential and script navigation", () => {
    expect(safeUrl("javascript:alert(1)")).toBe("#");
    expect(safeUrl("file:///private")).toBe("#");
  });
  it("encodes output filenames", () => {
    expect(fileUrl("base/my resume.pdf")).toBe(
      "/api/files/base/my%20resume.pdf",
    );
  });
  it("makes report limitations visible", () => {
    const html = renderToStaticMarkup(
      <ReportView
        report={{
          summary: "Role expectations",
          report: "## Skills\nSQL",
          sources: [],
          limitations: ["Hiring criteria are inferred"],
        }}
      />,
    );
    expect(html).toContain("Hiring criteria are inferred");
    expect(html).toContain("<h3>Skills</h3>");
  });
});

it("renders hiring comparisons as safe tables", () => {
  const html = renderToStaticMarkup(
    <RichText
      text={
        "| Skill | Evidence |\n|---|---|\n| SQL | <script>unsafe</script> |"
      }
    />,
  );
  expect(html).toContain("<table>");
  expect(html).toContain("<th>Skill</th>");
  expect(html).not.toContain("<script>");
});

it("shows cover-letter and removable-role actions without nesting buttons", () => {
  const html = renderToStaticMarkup(
    <JobList
      jobs={[
        {
          id: "job-1",
          company: "Example Co",
          title: "Data Analyst",
          location: "Austin, TX",
          url: "https://example.test/job-1",
          description:
            "A complete test job description for reporting and analytics.",
          status: "saved",
          notes: "",
          application_date: null,
          folder: null,
          created_at: "2026-09-15T10:00:00Z",
          selected_project_id: null,
          record_source: "posting",
          deleted_at: null,
          deletion_reason: "",
        },
      ]}
      onSelect={() => {}}
      onCoverLetter={() => {}}
      onRemove={() => {}}
    />,
  );
  expect(html).toContain("Cover letter");
  expect(html).toContain("Remove Example Co Data Analyst");
  expect(html).not.toContain("<button><button");
});

const baseJob: Omit<Job, "id" | "title" | "url" | "created_at"> = {
  company: "Example Co",
  location: "Austin, TX",
  description: "A complete test job description for data engineering.",
  status: "saved",
  notes: "",
  application_date: null,
  folder: null,
  selected_project_id: null,
  record_source: "posting",
  deleted_at: null,
  deletion_reason: "",
};

describe("Sponsorship tiers and exclusions", () => {
  it("shows the tier with its reason and lists best odds first", () => {
    const html = renderToStaticMarkup(
      <JobList
        jobs={[
          { ...baseJob, id: "c", title: "Silent Role", url: "https://example.test/c", created_at: "2026-09-17T10:00:00Z", sponsor_tier: "C" },
          { ...baseJob, id: "s", title: "University Role", url: "https://example.test/s", created_at: "2026-09-01T10:00:00Z", sponsor_tier: "S",
            sponsor_evidence: { tier: "S", label: "Cap-exempt: .edu domain" } },
          { ...baseJob, id: "b", title: "History Role", url: "https://example.test/b", created_at: "2026-09-10T10:00:00Z", sponsor_tier: "B" },
        ]}
        onSelect={() => {}}
      />,
    );
    expect(html).toContain("Tier S");
    expect(html).toContain('title="Cap-exempt: .edu domain"');
    expect(html).toContain(`title="${tierTitle.B}"`);
    // S (cap-exempt) before B (proven sponsor) before C (silent), regardless of date.
    const order = ["University Role", "History Role", "Silent Role"].map((t) => html.indexOf(t));
    expect(order.every((at) => at >= 0)).toBe(true);
    expect([...order].sort((a, b) => a - b)).toEqual(order);
    expect(html).toContain("All tiers");
  });

  it("treats a job with no tier yet as silent (C), never as excluded", () => {
    const html = renderToStaticMarkup(
      <TierBadge job={{ ...baseJob, id: "x", title: "Role", url: "https://example.test/x", created_at: "2026-09-17T10:00:00Z" }} long />,
    );
    expect(html).toContain("Tier C");
    expect(html).toContain(tierTitle.C);
  });

  it("lists excluded roles with the triggering sentence and a restore action", () => {
    const html = renderToStaticMarkup(
      <ExcludedRoles
        jobs={[
          {
            id: "ex-1",
            company: "Acme Corp",
            title: "Data Engineer",
            location: "Austin, TX",
            url: "https://acme.example/jobs/1",
            reason: "no_sponsorship",
            reason_label: "Says it will not sponsor",
            sentence: "Must be authorized to work in the US without sponsorship now or in the future.",
            source: "discovery",
            excluded_at: "2026-09-18T10:00:00Z",
          },
        ]}
        onRestore={() => {}}
      />,
    );
    expect(html).toContain("Excluded roles · 1");
    expect(html).toContain("without sponsorship now or in the future");
    expect(html).toContain("found by discovery");
    expect(html).toContain('href="https://acme.example/jobs/1"');
    expect(html).toContain("Restore");
    expect(renderToStaticMarkup(<ExcludedRoles jobs={[]} onRestore={() => {}} />)).toBe("");
  });
});
