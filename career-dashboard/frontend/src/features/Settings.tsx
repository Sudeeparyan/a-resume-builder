import { useCallback, useEffect, useState } from "react";
import {
  CheckCircle2,
  ExternalLink,
  Gauge,
  Globe,
  KeyRound,
  Mail,
  RefreshCw,
  Route,
  Trash2,
} from "lucide-react";
import { api } from "../api";
import { Badge, Field } from "../components/UI";
import { PROVIDER_LABEL } from "./Agents";

type Provider = {
  id: string;
  label: string;
  kind: "api" | "local";
  configured: boolean;
  models: string[];
  agent_models?: string[];
  capabilities?: string[];
  defaults: Record<string, string>;
  key_name?: string;
  key_source?: string | null;
  error?: string | null;
  note?: string;
};
type Choice = { provider: string; model: string };
type RouteRow = {
  action: string;
  label: string;
  provider: string | null;
  model: string | null;
  moved: boolean;
  override?: boolean;
  error: string | null;
};
type SettingsData = {
  main: Choice;
  routes: RouteRow[];
  providers: Provider[];
  tiers: Record<string, string>;
  preferences: { tiers: Record<string, Choice> };
};
type Budget = { daily_call_limit: number; calls_today: number; remaining_calls: number };

const KEY_PAGE: Record<string, string> = {
  openrouter: "https://openrouter.ai/keys",
  openai: "https://platform.openai.com/api-keys",
  anthropic: "https://console.anthropic.com/settings/keys",
  gemini: "https://aistudio.google.com/apikey",
  kimi: "https://platform.moonshot.ai/console/api-keys",
};
const TIER_LABEL: Record<string, string> = {
  strong: "Writing model",
  cheap: "Reading model",
};
const BLURB: Record<string, string> = {
  claude_code: "Your Claude plan's usage limits",
  codex: "Your ChatGPT plan · only one with Gmail",
  openai: "GPT models · has web search",
  anthropic: "Claude models, billed per call",
  openrouter: "Hundreds of models, one key",
  gemini: "Google's models · free tier",
  kimi: "Moonshot's Kimi models",
};
// Order on the page: the no-key options first.
const ORDER = ["claude_code", "codex", "openai", "anthropic", "openrouter", "gemini", "kimi"];

export default function Settings({
  notify,
}: {
  notify: (text: string, error?: boolean) => void;
}) {
  const [data, setData] = useState<SettingsData>();
  const [main, setMain] = useState<Choice>();
  const [busy, setBusy] = useState("");
  const [tested, setTested] = useState<Record<string, { ok: boolean; detail: string }>>({});
  const [keys, setKeys] = useState<Record<string, string>>({});
  const [keyResult, setKeyResult] = useState<Record<string, { ok: boolean; detail: string }>>({});
  const [tiers, setTiers] = useState<Record<string, Choice>>({});
  const [budget, setBudget] = useState<Budget>();
  const [limit, setLimit] = useState<number>();
  const [error, setError] = useState("");

  const load = useCallback(async (refresh = false) => {
    try {
      const [next, control] = await Promise.all([
        api<SettingsData>("/v2/ai/settings" + (refresh ? "?refresh=true" : "")),
        api<{ budget: Budget }>("/v2/agent-control"),
      ]);
      setData(next);
      setMain(next.main);
      setTiers(next.preferences.tiers);
      setBudget(control.budget);
      setLimit(control.budget.daily_call_limit);
      setError("");
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);
  useEffect(() => {
    void load();
  }, [load]);

  if (error) return <div className="callout warning">{error}</div>;
  if (!data || !main) return <p>Loading your AI settings…</p>;

  const byId = (id: string) => data.providers.find((p) => p.id === id);
  const providers = ORDER.map(byId).filter(Boolean) as Provider[];
  const chosen = byId(main.provider);
  const changed =
    main.provider !== data.main.provider || main.model !== data.main.model;
  const agentModels = chosen?.agent_models || [];

  async function act(name: string, fn: () => Promise<void>) {
    setBusy(name);
    try {
      await fn();
    } catch (e) {
      notify((e as Error).message, true);
    } finally {
      setBusy("");
    }
  }

  function pick(p: Provider) {
    if (!p.configured) {
      document.getElementById("key-" + p.id)?.focus();
      notify(
        p.kind === "api"
          ? `Add your ${p.label} API key below first.`
          : `${p.label} is not installed on this Mac.`,
        true,
      );
      return;
    }
    const models = p.agent_models || [];
    const preferred = p.defaults?.strong;
    setMain({
      provider: p.id,
      model: models.includes(preferred) ? preferred : models[0] || "",
    });
    setTested({});
  }

  const saveMain = () =>
    act("main", async () => {
      const next = await api<SettingsData>("/v2/ai/main", "PUT", main);
      setData(next);
      setMain(next.main);
      setTiers(next.preferences.tiers);
      notify(`All agents now run on ${PROVIDER_LABEL[main.provider] || main.provider} · ${main.model}.`);
    });

  const test = (choice: Choice, slot: string) =>
    act("test-" + slot, async () => {
      const result = await api<{ ok: boolean; detail: string }>(
        "/v2/ai/settings/test",
        "POST",
        choice,
      );
      setTested((t) => ({ ...t, [slot]: result }));
    });

  const saveKey = (p: Provider) =>
    act("key-" + p.id, async () => {
      const result = await api<{ ok: boolean; detail: string }>(
        "/v2/ai/keys/" + p.id,
        "PUT",
        { value: keys[p.id] || "" },
      );
      setKeys((k) => ({ ...k, [p.id]: "" }));
      setKeyResult((r) => ({ ...r, [p.id]: result }));
      notify(result.detail, !result.ok);
      await load();
    });

  const removeKey = (p: Provider) =>
    act("remove-" + p.id, async () => {
      if (!window.confirm(`Remove the ${p.label} key saved in the app?`)) return;
      const result = await api<{ detail: string }>("/v2/ai/keys/" + p.id, "DELETE");
      setKeyResult((r) => ({ ...r, [p.id]: { ok: true, detail: result.detail } }));
      notify(result.detail);
      await load();
    });

  const saveLimit = () =>
    act("limit", async () => {
      const next = await api<Budget>("/v2/agent-control/budget", "PUT", {
        daily_call_limit: limit ?? budget?.daily_call_limit,
      });
      setBudget(next);
      notify("Daily AI limit saved.");
    });

  return (
    <>
      <div className="page-title">
        <div>
          <div className="eyebrow">WHICH AI DOES THE WORK</div>
          <h1>Settings</h1>
          <p>
            Pick the AI that runs your agents and manage your API keys. Switching
            takes one click; nothing else needs to change.
          </p>
        </div>
        <button
          className="secondary"
          disabled={busy === "refresh"}
          onClick={() =>
            act("refresh", async () => {
              await load(true);
              notify("Provider status and model lists refreshed.");
            })
          }
        >
          <RefreshCw size={16} className={busy === "refresh" ? "spin" : ""} /> Refresh
        </button>
      </div>

      <section className="card">
        <div className="section-title">
          <h2>AI provider</h2>
          <Badge tone="green">
            In use: {PROVIDER_LABEL[data.main.provider] || data.main.provider} · {data.main.model}
          </Badge>
        </div>
        <p className="muted">
          Every agent uses this choice. Claude Code and Codex use your
          subscriptions on this Mac and need no key; the others need an API key
          (add it below).
        </p>
        {(
          [
            ["local", "No key needed — uses your subscription on this Mac"],
            ["api", "Pay-as-you-go with an API key"],
          ] as const
        ).map(([kind, heading]) => (
        <div key={kind}>
        <h3 className="provider-group">{heading}</h3>
        <div className="provider-grid" role="radiogroup" aria-label={heading}>
          {providers.filter((p) => p.kind === kind).map((p) => {
            const selected = main.provider === p.id;
            const caps = p.capabilities || [];
            return (
              <button
                key={p.id}
                role="radio"
                aria-checked={selected}
                className={"provider-tile" + (selected ? " selected" : "") + (p.configured ? "" : " unavailable")}
                onClick={() => pick(p)}
              >
                <span className="provider-tile-head">
                  <b>{PROVIDER_LABEL[p.id] || p.label}</b>
                  {selected && <CheckCircle2 size={18} />}
                </span>
                <small>{BLURB[p.id]}</small>
                <span className="provider-tile-tags">
                  <Badge tone={p.configured ? "green" : "amber"}>
                    {p.kind === "local"
                      ? p.configured ? "Ready" : "Not installed"
                      : p.configured ? "Key saved" : "Needs key"}
                  </Badge>
                  {caps.includes("web") && (
                    <Badge><Globe size={11} /> Web search</Badge>
                  )}
                  {caps.includes("apps") && (
                    <Badge><Mail size={11} /> Gmail</Badge>
                  )}
                </span>
              </button>
            );
          })}
        </div>
        </div>
        ))}

        <div className="main-choice">
          <Field label={`Model for ${PROVIDER_LABEL[main.provider] || "this provider"}`}>
            {agentModels.length > 25 ? (
              <>
                <input
                  list="agent-models"
                  value={main.model}
                  onChange={(e) => setMain({ ...main, model: e.target.value })}
                  placeholder="Type to search models"
                />
                <datalist id="agent-models">
                  {agentModels.map((m) => (
                    <option key={m} value={m} />
                  ))}
                </datalist>
              </>
            ) : (
              <select
                value={main.model}
                onChange={(e) => setMain({ ...main, model: e.target.value })}
              >
                {agentModels.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            )}
          </Field>
          <div className="actions">
            <button
              className="secondary"
              disabled={busy === "test-main" || !main.model}
              onClick={() => test(main, "main")}
            >
              {busy === "test-main" ? "Testing…" : "Test connection"}
            </button>
            <button
              className="primary"
              disabled={busy === "main" || !changed || !main.model}
              onClick={saveMain}
            >
              {busy === "main" ? "Saving…" : changed ? "Use for all agents" : "In use"}
            </button>
          </div>
        </div>
        {tested.main && (
          <div className={tested.main.ok ? "callout" : "callout warning"}>
            {tested.main.ok ? "Working. " : "Not working. "}
            {tested.main.detail}
          </div>
        )}
        {chosen?.note && <p className="small muted">{chosen.note}</p>}

        <div className="route-list">
          <h3>
            <Route size={16} /> Where each kind of work runs
          </h3>
          {data.routes.map((r) => (
            <div key={r.action} className="route-row">
              <span>{r.label}</span>
              {r.provider ? (
                <b>
                  {PROVIDER_LABEL[r.provider] || r.provider}
                  {r.model && r.model !== "codex-runtime" ? ` · ${r.model}` : ""}
                </b>
              ) : (
                <Badge tone="red">Not available</Badge>
              )}
              <small>
                {r.error
                  ? r.error
                  : r.override
                    ? "Chosen for this task in Resume Studio · picking a provider above resets it"
                    : r.moved
                    ? r.action === "email"
                      ? "Needs Gmail access, which only Codex has"
                      : "Needs web search, so it moves to a provider that has it"
                    : "Your main choice"}
              </small>
            </div>
          ))}
        </div>
      </section>

      <section className="card spaced">
        <div className="section-title">
          <h2>
            <KeyRound size={18} /> API keys
          </h2>
        </div>
        <p className="muted">
          Paste a key and press Save. It is checked straight away with a free
          call, kept only on this Mac (in <code>career-dashboard/.env</code>),
          and never shown on this page again.
        </p>
        <div className="key-list">
          {providers
            .filter((p) => p.kind === "api")
            .map((p) => {
              const result = keyResult[p.id];
              const fromApp = p.key_source === "saved in the app";
              return (
                <div key={p.id} className="key-row">
                  <div className="key-name">
                    <b>{PROVIDER_LABEL[p.id] || p.label}</b>
                    <Badge tone={p.configured ? (p.error ? "amber" : "green") : "neutral"}>
                      {p.configured
                        ? p.error
                          ? "Key has a problem"
                          : `Key set · ${p.key_source}`
                        : "No key"}
                    </Badge>
                    <a href={KEY_PAGE[p.id]} target="_blank" rel="noreferrer" className="small">
                      Get a key <ExternalLink size={11} />
                    </a>
                  </div>
                  <form
                    className="key-form"
                    onSubmit={(e) => {
                      e.preventDefault();
                      void saveKey(p);
                    }}
                  >
                    <input
                      id={"key-" + p.id}
                      type="password"
                      autoComplete="off"
                      spellCheck={false}
                      aria-label={`${p.label} API key`}
                      placeholder={p.configured ? "Paste a new key to replace it" : `Paste your ${p.label} key (${p.key_name})`}
                      value={keys[p.id] || ""}
                      onChange={(e) => setKeys((k) => ({ ...k, [p.id]: e.target.value }))}
                    />
                    <button
                      className="primary"
                      disabled={!keys[p.id]?.trim() || busy === "key-" + p.id}
                    >
                      {busy === "key-" + p.id ? "Checking…" : "Save & check"}
                    </button>
                    {fromApp && (
                      <button
                        type="button"
                        className="icon-button danger-icon"
                        title="Remove this key"
                        aria-label={`Remove the ${p.label} key`}
                        onClick={() => void removeKey(p)}
                      >
                        <Trash2 size={17} />
                      </button>
                    )}
                  </form>
                  {(result || p.error) && (
                    <small className={result?.ok ? "tone-done" : "tone-warn"}>
                      {result?.detail || p.error}
                    </small>
                  )}
                </div>
              );
            })}
        </div>
      </section>

      {budget && (
        <section className="card spaced">
          <div className="section-title">
            <h2>
              <Gauge size={18} /> Daily AI limit
            </h2>
            <Badge tone={budget.remaining_calls ? "green" : "amber"}>
              {budget.calls_today} of {budget.daily_call_limit} used today
            </Badge>
          </div>
          <p className="muted">
            A safety cap on AI calls per day, across every agent. Reused saved
            results do not count. Set 0 to allow only free checks.
          </p>
          <form
            className="actions"
            onSubmit={(e) => {
              e.preventDefault();
              void saveLimit();
            }}
          >
            <input
              className="limit-input"
              type="number"
              min={0}
              max={50}
              aria-label="Maximum AI calls per day"
              value={limit ?? budget.daily_call_limit}
              onChange={(e) => setLimit(Number(e.target.value))}
            />
            <button className="secondary" disabled={busy === "limit"}>
              Save limit
            </button>
          </form>
        </section>
      )}

      <details className="card spaced advanced">
        <summary>
          <b>Advanced: separate models for writing and reading</b>
          <small>Used by resume chat and profile chat. Choosing a provider above sets both.</small>
        </summary>
        {Object.keys(TIER_LABEL).map((tier) => {
          const choice = tiers[tier] || { provider: main.provider, model: "" };
          const provider = byId(choice.provider);
          return (
            <div className="tier-row" key={tier}>
              <div>
                <b>{TIER_LABEL[tier]}</b>
                <p className="small muted">{data.tiers[tier]}</p>
              </div>
              <select
                aria-label={`${TIER_LABEL[tier]} provider`}
                value={choice.provider}
                onChange={(e) => {
                  const p = byId(e.target.value);
                  setTiers((t) => ({
                    ...t,
                    [tier]: { provider: e.target.value, model: p?.defaults?.[tier] ?? p?.models?.[0] ?? "" },
                  }));
                }}
              >
                {providers
                  .filter((p) => p.id !== "codex")
                  .map((p) => (
                    <option key={p.id} value={p.id} disabled={!p.configured}>
                      {p.label}
                      {p.configured ? "" : " — not ready"}
                    </option>
                  ))}
              </select>
              <select
                aria-label={`${TIER_LABEL[tier]} model`}
                value={choice.model}
                onChange={(e) => setTiers((t) => ({ ...t, [tier]: { ...choice, model: e.target.value } }))}
              >
                {provider && !provider.models.includes(choice.model) && (
                  <option value={choice.model}>{choice.model}</option>
                )}
                {(provider?.models || []).map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
              <button
                className="secondary"
                disabled={busy === "test-" + tier}
                onClick={() => test(choice, tier)}
              >
                {busy === "test-" + tier ? "Testing…" : "Test"}
              </button>
              {tested[tier] && (
                <small className={tested[tier].ok ? "tone-done" : "tone-warn"}>
                  {tested[tier].detail}
                </small>
              )}
            </div>
          );
        })}
        <div className="actions">
          <button
            className="primary"
            disabled={busy === "tiers"}
            onClick={() =>
              act("tiers", async () => {
                await api("/v2/ai/settings", "PUT", { tiers });
                notify("Writing and reading models saved.");
                await load();
              })
            }
          >
            {busy === "tiers" ? "Saving…" : "Save these models"}
          </button>
        </div>
      </details>
    </>
  );
}
