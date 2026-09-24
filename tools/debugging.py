"""Safe parsing and explanation of developer command failures."""

import re
from typing import Any, Dict, List

from tools.registry import register_tool

ERROR_PATTERNS = [
    (re.compile(r"ModuleNotFoundError: No module named ['\"]([^'\"]+)['\"]"), "Install the missing Python dependency or fix the import path."),
    (re.compile(r"ImportError: (.+)"), "Check the package export and the active Python environment."),
    (re.compile(r"npm ERR! code (\S+)"), "Inspect npm's detailed error output and package scripts."),
    (re.compile(r"AssertionError: (.*)"), "Compare the failing expectation with the current behavior and inspect the referenced test."),
    (re.compile(r"(?:SyntaxError|IndentationError): (.*)"), "Open the referenced file and correct the syntax or indentation."),
    (re.compile(r"Permission denied: (.*)"), "Check file ownership and avoid granting broad permissions."),
]


def explain_failure(output: str, limit: int = 20) -> Dict[str, Any]:
    """Extract common failures and provide bounded next-step suggestions."""
    text = (output or "").strip()
    if not text:
        return {"success": False, "error": "Failure output cannot be empty."}

    findings: List[Dict[str, str]] = []
    for line in text.splitlines():
        for pattern, suggestion in ERROR_PATTERNS:
            match = pattern.search(line)
            if match:
                findings.append({
                    "line": line[:500],
                    "type": pattern.pattern,
                    "suggestion": suggestion,
                })
                break
        if len(findings) >= max(1, min(limit, 100)):
            break

    if not findings and ("failed" in text.lower() or "error" in text.lower()):
        findings.append({
            "line": "No recognized structured error line was found.",
            "type": "unknown",
            "suggestion": "Review the final error block and rerun the smallest failing command with verbose output.",
        })

    return {
        "success": True,
        "count": len(findings),
        "findings": findings,
        "message": "Failure analysis completed." if findings else "No failures detected in the supplied output.",
    }


@register_tool({
    "name": "explain_developer_failure",
    "description": "Analyze test or terminal output and suggest safe next steps without changing files.",
    "input_schema": {
        "type": "object",
        "properties": {
            "output": {"type": "string", "description": "Test or terminal output to analyze."},
            "limit": {"type": "integer", "description": "Maximum number of findings."},
        },
        "required": ["output"],
    },
})
def explain_developer_failure(output: str, limit: int = 20) -> Dict[str, Any]:
    return explain_failure(output, limit)
