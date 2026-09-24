from tools.developer_workflow import prepare_project


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
