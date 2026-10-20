"""Agent runs keep the span that started them, and the run's event log links to its trace."""

from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

from test_career_workspace import workspace  # noqa: F401 - fixture
from test_workspace_v2 import service  # noqa: F401 - fixture

from backend import telemetry
from backend.services.agents import AgentRunner


def test_agent_submission_keeps_parent_and_event_ids(spans, service, monkeypatch):
    runner = AgentRunner(service)
    # No AI provider is reached: resolving and running are replaced, enqueueing is real.
    monkeypatch.setattr(runner.gateway, "resolve", lambda action, provider=None, model=None, **k: (SimpleNamespace(id="codex"), "codex-runtime"))

    def work(run_id):
        runner.trace.stage = "Checking posting"
        runner.trace_event("stage", "Checking posting", run_id=run_id)
        runner.update(run_id, "completed", {"summary": "synthetic"})

    runner._run = work
    try:
        with telemetry.span("pipeline.run") as parent:
            task = runner.enqueue("discovery", preset="portals")
            runner.pool.shutdown(wait=True)
        calls = [s for s in spans.get_finished_spans() if s.name == "agent.run discovery"]
        assert len(calls) == 1 and calls[0].parent.span_id == parent.get_span_context().span_id
        assert calls[0].attributes["career.run_id"] == task["id"]
        with service.w.connect() as db:
            event = db.execute(
                "SELECT trace_id,span_id,node FROM agent_run_events WHERE run_id=? AND kind='stage' "
                "AND label='Checking posting'", (task["id"],),
            ).fetchone()
        assert event["trace_id"] == f"{calls[0].context.trace_id:032x}"
        assert event["span_id"] == f"{calls[0].context.span_id:016x}"
        assert event["node"] == "Checking posting"
    finally:
        runner.pool.shutdown(wait=True)


def test_worker_context_is_reset_between_runs(spans):
    def work():
        with telemetry.span("worker"):
            return telemetry.current_profile_root(), telemetry.current_run()

    with ThreadPoolExecutor(max_workers=1) as pool:
        with telemetry.bind(profile_root="workspace-one", run={"id": "one"}):
            assert telemetry.submit(pool, work).result() == ("workspace-one", {"id": "one"})
        with telemetry.bind(profile_root="workspace-two", run={"id": "two"}):
            assert telemetry.submit(pool, work).result() == ("workspace-two", {"id": "two"})
        assert pool.submit(work).result() == (None, None)


def test_antigravity_is_a_free_plan_on_the_route_before_paid_azure(tmp_path, monkeypatch):
    from backend.ai import limits, router

    monkeypatch.setattr(router, "model_for", lambda _root, provider, _tier: provider + "-model")
    assert router.FREE == ("kimi_cli", "codex", "claude_code", "antigravity_cli")
    assert router.ordered(router.default_policy())[-1] == "azure_openai"
    book = limits.HealthBook(tmp_path)
    for provider in ("kimi_cli", "codex", "claude_code"):
        book.rest_for_limit(provider, "usage limit reached")
    ready = {provider: True for provider in router.DEFAULT_ORDER}
    result, served = router.route(tmp_path, tier="strong", attempt=lambda p, m: {"by": p},
                                  ready_map=ready, book=book, paid_gate=lambda _p: "should not reach Azure")
    assert served == ("antigravity_cli", "antigravity_cli-model") and result == {"by": "antigravity_cli"}
