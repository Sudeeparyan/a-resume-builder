/**
 * Dark by default, light as a deliberate choice.
 *
 * Nothing here reads prefers-color-scheme. The choice is explicit and sticky
 * rather than inherited from the OS, because a resume-editing tool that
 * silently flips because someone's laptop is set that way is exactly the kind
 * of surprise that makes an app feel unpredictable.
 */
export type Theme = "light" | "dark";

const KEY = "dashboard-theme";
const DEFAULT: Theme = "dark";

export function getTheme(): Theme {
  try {
    const saved = localStorage.getItem(KEY);
    if (saved === "light" || saved === "dark") return saved;
  } catch {
    /* private browsing, blocked site data -- fall through to the default */
  }
  return DEFAULT;
}

export function applyTheme(theme: Theme): void {
  document.documentElement.setAttribute("data-theme", theme);
  try {
    localStorage.setItem(KEY, theme);
  } catch {
    /* nothing to persist to; the in-memory choice still applies this load */
  }
}

export function initTheme(): Theme {
  const t = getTheme();
  applyTheme(t);
  return t;
}
