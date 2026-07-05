import argparse
import os
from pathlib import Path
import subprocess
import sys


def _run(cmd: list[str]) -> int:
    print(f"\n$ {' '.join(cmd)}")
    return subprocess.run(cmd, check=False).returncode


def _discover_unit_modules(project_root: str, include_e2e: bool) -> list[str]:
    test_dir = Path(project_root) / "auto_test"
    modules: list[str] = []
    for path in sorted(test_dir.glob("test_*.py")):
        if path.stem == "test_agent_os_e2e" and not include_e2e:
            continue
        modules.append(f"auto_test.{path.stem}")
    return modules


def main() -> int:
    parser = argparse.ArgumentParser(description="Run AC-OS automated test suites.")
    parser.add_argument(
        "--include-e2e",
        action="store_true",
        help="Also run E2E chaos matrix (requires API key).",
    )
    args = parser.parse_args()

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)

    unit_modules = _discover_unit_modules(project_root, include_e2e=False)
    unit_rc = _run([sys.executable, "-m", "unittest", "-v", *unit_modules])
    if unit_rc != 0:
        return unit_rc

    if not args.include_e2e:
        print("\n[OK] Unit suites passed. Skipping E2E (use --include-e2e to run).")
        return 0

    api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("\n[SKIP] E2E skipped: missing DEEPSEEK_API_KEY / OPENAI_API_KEY.")
        return 0

    e2e_rc = _run([sys.executable, "-m", "unittest", "-v", "auto_test.test_agent_os_e2e"])
    return e2e_rc


if __name__ == "__main__":
    raise SystemExit(main())
