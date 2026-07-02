from pathlib import Path


WORKFLOW_PATH = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "dev-health.yml"


def test_dev_health_workflow_runs_non_mutating_diagnostics() -> None:
    workflow_content = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "python scripts/provider_readiness.py --provider mock --market US" in workflow_content
    assert "python scripts/task_run_health.py" in workflow_content
    assert "tests/scripts/test_provider_readiness.py" in workflow_content
    assert "tests/scripts/test_task_run_health.py" in workflow_content
