#!/usr/bin/env python3
"""
Preflight environment validation for agent-creator.

Checks that the environment has everything needed to create and test agents.
Run before Phase 4 (testing) to catch issues early.

Usage:
    python preflight.py [--output-dir PATH] [--json]

Exit codes:
    0 - All checks passed
    1 - One or more checks failed
"""

import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def check_python_version(min_version=(3, 8)):
    """Check Python version is sufficient."""
    current = sys.version_info[:2]
    passed = current >= min_version
    return {
        "check": "python_version",
        "passed": passed,
        "current": f"{current[0]}.{current[1]}",
        "required": f"{min_version[0]}.{min_version[1]}+",
        "message": f"Python {current[0]}.{current[1]}" if passed
                   else f"Python {current[0]}.{current[1]} found, need {min_version[0]}.{min_version[1]}+"
    }


def check_claude_cli():
    """Check if claude CLI is available and get version."""
    claude_path = shutil.which("claude")
    if not claude_path:
        return {
            "check": "claude_cli",
            "passed": False,
            "path": None,
            "version": None,
            "message": "'claude' command not found. Install Claude CLI first."
        }

    try:
        result = subprocess.run(
            ["claude", "--version"],
            capture_output=True, text=True, timeout=10
        )
        version = result.stdout.strip() or result.stderr.strip()
        return {
            "check": "claude_cli",
            "passed": True,
            "path": claude_path,
            "version": version,
            "message": f"Claude CLI found: {version}"
        }
    except subprocess.TimeoutExpired:
        return {
            "check": "claude_cli",
            "passed": True,
            "path": claude_path,
            "version": "unknown (timeout)",
            "message": "Claude CLI found but version check timed out"
        }
    except OSError as e:
        return {
            "check": "claude_cli",
            "passed": False,
            "path": claude_path,
            "version": None,
            "message": f"Claude CLI found but cannot execute: {e}"
        }


def check_write_permission(output_dir=None):
    """Check write permission on output directory."""
    target = Path(output_dir) if output_dir else Path.cwd()
    try:
        target.mkdir(parents=True, exist_ok=True)
        test_file = target / '.preflight_test'
        test_file.write_text('test')
        test_file.unlink()
        return {
            "check": "write_permission",
            "passed": True,
            "path": str(target),
            "message": f"Write access OK: {target}"
        }
    except (OSError, PermissionError) as e:
        return {
            "check": "write_permission",
            "passed": False,
            "path": str(target),
            "message": f"Cannot write to {target}: {e}"
        }


def check_disk_space(path=None, min_mb=100):
    """Check available disk space."""
    target = path or str(Path.cwd())
    try:
        usage = shutil.disk_usage(target)
        free_mb = usage.free / (1024 * 1024)
        passed = free_mb >= min_mb
        return {
            "check": "disk_space",
            "passed": passed,
            "free_mb": round(free_mb, 1),
            "required_mb": min_mb,
            "message": f"{round(free_mb, 1)} MB free" if passed
                       else f"Only {round(free_mb, 1)} MB free (need {min_mb} MB)"
        }
    except OSError as e:
        return {
            "check": "disk_space",
            "passed": False,
            "free_mb": 0,
            "required_mb": min_mb,
            "message": f"Cannot check disk space: {e}"
        }


def check_platform():
    """Report platform info (always passes, informational)."""
    return {
        "check": "platform",
        "passed": True,
        "os": platform.system(),
        "version": platform.version(),
        "arch": platform.machine(),
        "message": f"{platform.system()} {platform.machine()}"
    }


def run_preflight(output_dir=None, as_json=False):
    """Run all preflight checks.

    Args:
        output_dir: Optional directory to check write permissions for
        as_json: If True, return JSON string instead of printing

    Returns:
        dict with all check results and overall status
    """
    checks = [
        check_python_version(),
        check_claude_cli(),
        check_write_permission(output_dir),
        check_disk_space(output_dir),
        check_platform(),
    ]

    all_passed = all(c["passed"] for c in checks)

    result = {
        "passed": all_passed,
        "checks": checks,
        "summary": {
            "total": len(checks),
            "passed": sum(1 for c in checks if c["passed"]),
            "failed": sum(1 for c in checks if not c["passed"])
        }
    }

    if as_json:
        return json.dumps(result, indent=2, ensure_ascii=False)

    # Human-readable output
    for check in checks:
        icon = "OK" if check["passed"] else "FAIL"
        print(f"  [{icon}] {check['check']}: {check['message']}")

    print()
    if all_passed:
        print("All preflight checks passed.")
    else:
        failed = [c for c in checks if not c["passed"]]
        print(f"FAILED: {len(failed)} check(s) did not pass.")
        for c in failed:
            print(f"  - {c['check']}: {c['message']}")

    return result


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Preflight environment validation')
    parser.add_argument('--output-dir', help='Directory to check write permissions for')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    args = parser.parse_args()

    result = run_preflight(args.output_dir, args.json)

    if args.json:
        print(result)
        sys.exit(0 if json.loads(result)["passed"] else 1)
    else:
        sys.exit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
