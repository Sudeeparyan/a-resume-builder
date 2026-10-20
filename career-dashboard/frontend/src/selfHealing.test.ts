import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "./api";

// Ported from the Template (October 2026): reads mend themselves while the app restarts
// (the morning run may restart it); writes are never repeated.
const json = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

describe("reads mend themselves", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it("waits and retries a read while the app restarts", async () => {
    vi.useFakeTimers();
    const fetch = vi
      .spyOn(globalThis, "fetch")
      .mockRejectedValueOnce(new TypeError("Failed to fetch"))
      .mockResolvedValueOnce(new Response("<html>Bad gateway</html>", { status: 502 }))
      .mockResolvedValueOnce(json(200, { ok: true }));
    const result = api("/v2/summary");
    await vi.runAllTimersAsync();
    await expect(result).resolves.toEqual({ ok: true });
    expect(fetch).toHaveBeenCalledTimes(3);
  });

  it("never repeats a write, and says plainly what happened", async () => {
    const fetch = vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("Failed to fetch"));
    await expect(api("/v2/pipeline/run", "POST", {})).rejects.toThrow("may be restarting");
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it("does not retry the app's own answer to a bad request", async () => {
    const fetch = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(json(400, { detail: "Choose between 1 and 5 jobs." }));
    await expect(api("/v2/pipeline")).rejects.toThrow("Choose between 1 and 5 jobs");
    expect(fetch).toHaveBeenCalledTimes(1);
  });
});
