import argparse
import datetime as dt
import subprocess
from pathlib import Path
from typing import List


DEFAULT_REPORT = Path(__file__).resolve().parent / "auto_test_report.md"


def _pick_key_lines(output: str, limit: int = 12) -> List[str]:
    lines = [line.rstrip() for line in output.splitlines() if line.strip()]
    selected: List[str] = []
    preferred_prefix = ("test_", "Ran ", "OK", "FAILED", "Profile:", "[OK]", "[SKIP]", "[FAIL]", "Result:")
    for line in lines:
        if line.startswith(preferred_prefix):
            selected.append(line)
    if not selected:
        selected = lines[-limit:]
    return selected[-limit:]


def _append_success_report(report_path: Path, command: str, output: str) -> None:
    timestamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M (UTC+8)")
    key_lines = _pick_key_lines(output)
    block_lines = [
        "",
        f"### {timestamp}",
        "",
        f"- Command: `{command}`",
        "- Result: PASS",
        "- Details:",
    ]
    block_lines.extend([f"  - {line}" for line in key_lines])
    block_lines.append("")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("a", encoding="utf-8") as f:
        f.write("\n".join(block_lines))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a test command and append report only on success.")
    parser.add_argument("--report", default=str(DEFAULT_REPORT), help="Markdown report path.")
    parser.add_argument("--cmd", required=True, help="Command to execute, e.g. 'python3 auto_test/run_all.py'.")
    args = parser.parse_args()

    completed = subprocess.run(args.cmd, shell=True, capture_output=True, text=True, check=False)
    if completed.stdout:
        print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, end="")

    if completed.returncode != 0:
        print("\n[REPORT] skipped: command failed, report not updated.")
        return completed.returncode

    _append_success_report(Path(args.report), args.cmd, completed.stdout)
    print(f"\n[REPORT] appended success record -> {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
