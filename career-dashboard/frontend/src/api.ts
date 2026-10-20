export const API_BASE = "/api";

/** Waits (ms) before each retry of a read that failed for a passing reason. */
export const RETRY_WAITS = [800, 2500, 6000];
const PASSING_STATUS = new Set([502, 503, 504]);

class RequestError extends Error {
  constructor(message: string, readonly passing: boolean) {
    super(message);
  }
}

async function request<T>(
  url: string,
  method: string,
  body: unknown,
  options: { timeout?: number; raw?: Blob },
): Promise<T> {
  // A read is safe to repeat: while the app restarts (the morning run may restart it) or the
  // connection drops for a moment, it waits and tries again instead of showing an error at
  // once. Polls (with a timeout) retry on their own schedule; writes are never repeated.
  const tries = method === "GET" && !options.timeout ? RETRY_WAITS.length + 1 : 1;
  for (let attempt = 1; ; attempt++) {
    try {
      return await once<T>(url, method, body, options);
    } catch (e) {
      if (attempt >= tries || !(e instanceof RequestError && e.passing)) throw e;
      await new Promise((resolve) => setTimeout(resolve, RETRY_WAITS[attempt - 1]));
    }
  }
}

async function once<T>(
  url: string,
  method: string,
  body: unknown,
  options: { timeout?: number; raw?: Blob },
): Promise<T> {
  const control = options.timeout ? new AbortController() : null;
  const timer = control ? setTimeout(() => control.abort(), options.timeout) : undefined;
  let r: Response;
  try {
    r = await fetch(url, {
      method,
      headers: options.raw
        ? { "Content-Type": "application/octet-stream" }
        : body === undefined
          ? {}
          : { "Content-Type": "application/json" },
      body: options.raw ?? (body === undefined ? undefined : JSON.stringify(body)),
      signal: control?.signal,
    });
  } catch (e) {
    throw new RequestError(
      control?.signal.aborted
        ? "The app did not answer in time. Retrying…"
        : "The app is not answering right now (it may be restarting). Try again in a moment.",
      true,
    );
  } finally {
    if (timer !== undefined) clearTimeout(timer);
  }
  let data: any;
  try {
    data = await r.json();
  } catch {
    // Not the app's JSON: a restart in progress or something in between answered.
    throw new RequestError(
      `The app is not ready yet (it answered ${r.status}). Try again in a moment.`,
      !r.ok || PASSING_STATUS.has(r.status),
    );
  }
  if (!r.ok)
    throw new RequestError(
      typeof data?.detail === "string" ? data.detail : JSON.stringify(data?.detail || data),
      PASSING_STATUS.has(r.status),
    );
  return data;
}

export function api<T = any>(
  path: string,
  method = "GET",
  body?: unknown,
  options: { timeout?: number } = {},
): Promise<T> {
  return request<T>(API_BASE + path, method, body, options);
}

/** Send one file as the request body (no multipart); `url` is a full path. */
export function uploadFile<T = any>(url: string, file: Blob, name: string): Promise<T> {
  const joiner = url.includes("?") ? "&" : "?";
  return request<T>(url + joiner + "name=" + encodeURIComponent(name), "POST", undefined, { raw: file });
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
  API_BASE + "/files/" + path.split("/").map(encodeURIComponent).join("/");
