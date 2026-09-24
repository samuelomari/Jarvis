from tools.developer_workflow import prepare_project
from tools.debugging import explain_failure
from tools.computer_control import run_terminal_command


def test_prepare_project_reports_project_and_skips_side_effects():
    result = prepare_project(path=".", run_tests=False)

    assert result["success"] is True
    assert result["project"] == "."
    assert result["failed_steps"] == []
    assert any(step["name"] == "inspect" for step in result["steps"])
    install_step = next(step for step in result["steps"] if step["name"] == "install_dependencies")
    assert install_step["skipped"] is True


def test_prepare_project_rejects_paths_outside_workspace():
    result = prepare_project(path="..", run_tests=False)

    assert result["success"] is False
    assert "Invalid project path" in result["error"]


def test_explain_failure_extracts_actionable_findings():
    result = explain_failure("ModuleNotFoundError: No module named 'fastapi'")

    assert result["success"] is True
    assert result["count"] == 1
    assert "dependency" in result["findings"][0]["suggestion"]


def test_terminal_control_requires_confirmation_and_workspace_cwd():
    blocked = run_terminal_command("rm -rf ./tmp", confirmed=False)
    assert blocked["success"] is False
    assert blocked["needs_confirmation"] is True

    outside = run_terminal_command("printf safe", cwd="..")
    assert outside["success"] is False
    assert "inside the project workspace" in outside["error"]
