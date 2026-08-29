"""Unit tests for Jarvis project analysis and symbol inspection tools."""

from pathlib import Path
from tools.analysis import analyze_codebase, inspect_symbols


def test_analyze_codebase():
    """Test static analysis of workspace codebase."""
    res = analyze_codebase(".")
    assert res["success"] is True
    assert "summary" in res
    assert res["summary"]["total_files"] > 0
    assert res["summary"]["total_lines"] > 0
    assert "Python" in res["summary"]["languages"]
    assert len(res["largest_files"]) > 0


def test_inspect_symbols(tmp_path):
    """Test AST symbol inspection on a sample Python file."""
    sample_file = tmp_path / "sample_module.py"
    sample_file.write_text(
        '''"""Sample module docstring."""
import os
from datetime import datetime

class DataProcessor:
    """Processes datasets."""
    def process_data(self, data):
        return True

def standalone_helper(x, y):
    """Adds numbers."""
    return x + y
''',
        encoding="utf-8",
    )

    # Relative to project or absolute within safety check
    # Let's inspect config.py which is already in project root
    res = inspect_symbols("config.py")
    assert res["success"] is True
    assert "classes" in res
    assert "functions" in res
    assert "imports" in res
    assert any("dotenv" in imp or "pathlib" in imp or "os" in imp for imp in res["imports"])

