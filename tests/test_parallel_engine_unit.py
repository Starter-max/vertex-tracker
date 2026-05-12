import inspect
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
BACKEND = ROOT / "dashboard" / "backend"
sys.path.insert(0, str(BACKEND))

import main
import parallel_engine


def test_requested_subtasks_are_normalized_with_safe_defaults():
    subtasks = parallel_engine.split_into_subtasks(
        "objective",
        requested=[{"title": "A"}, {"title": "B", "dependency_ids": ["A"], "metadata": {"x": 1}}],
    )

    assert [s["title"] for s in subtasks] == ["A", "B"]
    assert subtasks[0]["instructions"] == "A"
    assert subtasks[0]["priority"] == "P2"
    assert subtasks[0]["parallel_group_id"] == "main"
    assert subtasks[1]["dependency_ids"] == ["A"]
    assert subtasks[1]["metadata"] == {"x": 1}


def test_default_decomposition_preserves_safety_flow():
    subtasks = parallel_engine.split_into_subtasks("build additive layer")
    titles = [s["title"] for s in subtasks]

    assert titles[0].startswith("diagnostics")
    assert titles[1].startswith("backups")
    assert titles[2].startswith("implementation")
    assert titles[3].startswith("verification")
    assert subtasks[1]["dependency_ids"] == ["diagnostics"]
    assert subtasks[2]["dependency_ids"] == ["backups"]
    assert subtasks[3]["dependency_ids"] == ["implementation"]
    assert all(s["metadata"].get("destructive") is False for s in subtasks)


def test_worker_safe_defaults_and_cli_guardrails_are_encoded():
    sig = inspect.signature(parallel_engine.execute_running_subtasks)
    assert sig.parameters["max_items"].default == 1
    assert sig.parameters["allow_cli"].default is False
    assert sig.parameters["timeout_seconds"].default == 120

    source = inspect.getsource(parallel_engine.execute_running_subtasks)
    assert "max(1, min(int(max_items or 1), 5))" in source
    assert "max(15, min(int(timeout_seconds or 120), 600))" in source
    assert "/Users/admin/.local/bin/hermes" in source
    assert "NEEDS_OWNER_DECISION" in source
    assert "DRY_RUN worker tick" in source


def test_parallel_api_routes_and_safety_clamps_are_encoded():
    route_paths = {getattr(route, "path", None) for route in main.app.routes}
    assert "/api/parallel/work-packages" in route_paths
    assert "/api/parallel/dispatcher/tick" in route_paths
    assert "/api/parallel/worker/tick" in route_paths

    dispatcher_source = inspect.getsource(main.api_parallel_dispatcher_tick)
    assert "max(1, min(int(safe_limit), 10))" in dispatcher_source
    assert "dispatch_ready_subtasks" in dispatcher_source

    worker_source = inspect.getsource(main.api_parallel_worker_tick)
    assert "max(1, min(int(body.max_items or 1), 5))" in worker_source
    assert "max(15, min(int(body.timeout_seconds or 120), 600))" in worker_source
    assert "allow_cli=bool(body.allow_cli)" in worker_source
    assert "execute_running_subtasks" in worker_source

    assert main.ParallelWorkerTickBody().max_items == 1
    assert main.ParallelWorkerTickBody().allow_cli is False
    assert main.ParallelWorkerTickBody().timeout_seconds == 120


def test_parallel_engine_seed_contains_virtual_agent_for_fk_safety():
    source = inspect.getsource(parallel_engine.ensure_parallel_migration)
    assert "parallel-engine" in source
    assert "INSERT INTO agents" in source


def test_worker_guardrails_require_diagnostics_backup_and_owner_decision_for_risks():
    safe = parallel_engine.evaluate_worker_guardrails(
        allow_cli=True,
        work_package={"diagnostic_ref": "diag-ok", "backup_ref": "backup-ok", "requires_backup": True},
        subtask_metadata={"destructive": False, "touches_env": False},
    )
    assert safe["allowed"] is True
    assert safe["reasons"] == []

    unsafe = parallel_engine.evaluate_worker_guardrails(
        allow_cli=True,
        work_package={"diagnostic_ref": None, "backup_ref": None, "requires_backup": True},
        subtask_metadata={"destructive": True, "touches_secrets": True, "owner_decision_id": None},
    )
    assert unsafe["allowed"] is False
    assert "missing_diagnostic_ref" in unsafe["reasons"]
    assert "missing_backup_ref" in unsafe["reasons"]
    assert "risky_flag:destructive" in unsafe["reasons"]
    assert "risky_flag:touches_secrets" in unsafe["reasons"]
    assert unsafe["requires_owner_decision"] is True


def test_owner_summary_and_worker_metrics_are_encoded():
    summary = parallel_engine.build_work_package_result_summary([
        {"title": "A", "status": "done", "result_summary": "alpha"},
        {"title": "B", "status": "failed", "error_summary": "boom"},
        {"title": "C", "status": "needs_review", "result_summary": "needs owner"},
    ])
    assert "done=1" in summary
    assert "failed=1" in summary
    assert "needs_review=1" in summary
    assert "A: alpha" in summary
    assert "B: ERROR boom" in summary

    source = inspect.getsource(parallel_engine.execute_running_subtasks)
    assert "worker_tick_summary" in source
    assert "duration_seconds" in source
    assert "failed_count" in source
    assert "timeout_count" in source
    assert "guardrail_blocked_count" in source


if __name__ == "__main__":
    tests = [
        test_requested_subtasks_are_normalized_with_safe_defaults,
        test_default_decomposition_preserves_safety_flow,
        test_worker_safe_defaults_and_cli_guardrails_are_encoded,
        test_parallel_api_routes_and_safety_clamps_are_encoded,
        test_parallel_engine_seed_contains_virtual_agent_for_fk_safety,
        test_worker_guardrails_require_diagnostics_backup_and_owner_decision_for_risks,
        test_owner_summary_and_worker_metrics_are_encoded,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
