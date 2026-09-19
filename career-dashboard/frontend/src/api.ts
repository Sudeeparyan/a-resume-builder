export async function api<T = any>(
  path: string,
  method = "GET",
  body?: unknown,
  options: { timeout?: number } = {},
): Promise<T> {
  // A poll that never answers (a dropped connection, a sleeping laptop) must fail,
  // not hang the loop that would retry it.
  const control = options.timeout ? new AbortController() : undefined;
  const timer = control ? window.setTimeout(() => control.abort(), options.timeout) : 0;
  let r: Response;
  try {
    r = await fetch("/api" + path, {
      method,
      headers: body === undefined ? {} : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: control?.signal,
    });
  } catch (e) {
    throw new Error(control?.signal.aborted ? "The app did not answer in time. Retrying…" : "Cannot reach the app: " + (e as Error).message);
  } finally {
    window.clearTimeout(timer);
  }
  const data = await r.json();
  if (!r.ok)
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : JSON.stringify(data.detail || data),
    );
  return data;
}
export const safeUrl = (value: string) => {
  try {
    const u = new URL(value);
    return ["https:", "http:"].includes(u.protocol) &&
      !u.username &&
      !u.password
      ? u.href
      : "#";
  } catch {
    return "#";
  }
};
export const fileUrl = (path: string) =>
  "/api/files/" + path.split("/").map(encodeURIComponent).join("/");
