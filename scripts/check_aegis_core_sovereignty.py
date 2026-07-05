#!/usr/bin/env python3
"""
Sovereignty guard for AC-OS Aegis core.

Rule: `core_aegis/` must not contain autonomous orchestration constructs.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
AEGIS_CORE_DIR = REPO_ROOT / "core_aegis"

FORBIDDEN_PATTERNS = {
    r"\bStateGraph\b": "LangGraph StateGraph orchestration is forbidden in core path.",
    r"^\s*from\s+langgraph\b": "LangGraph imports/usages are forbidden in core path.",
    r"^\s*import\s+langgraph\b": "LangGraph imports/usages are forbidden in core path.",
    r"\bwhile\s+": "Autonomous while-loops are forbidden in Aegis core path.",
    r"^\s*from\s+streamlit\b": "UI runtime logic is forbidden in Aegis core path.",
    r"^\s*import\s+streamlit\b": "UI runtime logic is forbidden in Aegis core path.",
}


def _iter_python_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(p for p in root.rglob("*.py") if p.is_file())


def main() -> int:
    violations: list[str] = []
    for py_file in _iter_python_files(AEGIS_CORE_DIR):
        content = py_file.read_text(encoding="utf-8")
        for pattern, reason in FORBIDDEN_PATTERNS.items():
            for match in re.finditer(pattern, content, flags=re.IGNORECASE | re.MULTILINE):
                line_no = content.count("\n", 0, match.start()) + 1
                relative_path = py_file.relative_to(REPO_ROOT)
                violations.append(
                    f"{relative_path}:{line_no}: '{match.group(0)}' -> {reason}"
                )

    if violations:
        print("AC-OS sovereignty guard FAILED.")
        print("Detected forbidden constructs under core_aegis/:")
        for item in violations:
            print(f"- {item}")
        return 1

    print("AC-OS sovereignty guard PASSED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
