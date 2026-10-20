import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { NeedsYou } from "./Dashboard";

describe("NeedsYou", () => {
  it("lists what only Annie can do, with the page that resolves it", () => {
    const html = renderToStaticMarkup(
      <NeedsYou
        onGo={() => {}}
        items={[
          { id: "ai_signed_out", text: "Kimi Code is signed out, so tailoring and study plans cannot run on it.", where: "settings" },
          { id: "assurance_pending", text: "7 suggested resume items wait for your keep or remove in Assurance.", where: "assurance",
            job_ids: ["j1"] },
          { id: "open_questions", text: "11 questions in your profile still need your answer.", where: "profile" },
        ]}
      />,
    );
    expect(html).toContain("Needs you");
    expect(html).toContain("Kimi Code is signed out");
    expect(html).toContain("Open Settings");
    expect(html).toContain("Open Assurance");
    expect(html).toContain("Open Profile");
  });

  it("shows nothing when nothing needs her", () => {
    expect(renderToStaticMarkup(<NeedsYou items={[]} />)).toBe("");
  });
});
