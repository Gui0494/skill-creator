#!/usr/bin/env python3
"""
Auto-correction analysis for failed agent tests.

Reads test-results.json, extracts FAIL verdicts, maps failures to
likely root causes in the agent's files, and produces a structured
correction plan. This script provides the analytical foundation for
Phase 5 (Auto-Correction) — it tells you WHAT broke and WHERE to fix,
so the LLM or developer can apply the fixes.

Usage:
    python auto_correct.py <agent-path> <workspace-path> [--iteration N] [--json]

Output:
    Structured analysis of failures with suggested fixes per file.
"""

import json
import re
import sys
from pathlib import Path


# ─── Failure pattern recognition ────────────────────────────────────

FAILURE_PATTERNS = [
    {
        "pattern": r"not found|missing|does not exist|no such file",
        "category": "missing_resource",
        "suggestion": "A referenced file or resource is missing. Check paths in SKILL.md and scripts.",
    },
    {
        "pattern": r"ambiguous|unclear|vague|confus",
        "category": "ambiguous_instruction",
        "suggestion": "Instructions in SKILL.md are too vague. Add specific steps, templates, or examples.",
    },
    {
        "pattern": r"format|structure|template|schema",
        "category": "output_format",
        "suggestion": "Output format doesn't match expectations. Add an explicit output template to SKILL.md.",
    },
    {
        "pattern": r"error|exception|traceback|failed|crash",
        "category": "script_error",
        "suggestion": "A script has a bug. Check scripts/ directory for syntax or logic errors.",
    },
    {
        "pattern": r"timeout|slow|hung|exceed",
        "category": "performance",
        "suggestion": "Execution took too long. Simplify the task or add timeout handling.",
    },
    {
        "pattern": r"edge case|unexpected input|invalid|empty",
        "category": "edge_case",
        "suggestion": "An edge case wasn't handled. Add explicit edge case handling to SKILL.md.",
    },
    {
        "pattern": r"trigger|activate|invoke|skill not used",
        "category": "trigger_failure",
        "suggestion": "The skill wasn't triggered. Make the description more 'pushy' with more trigger phrases.",
    },
]


def classify_failure(evidence):
    """Classify a failure based on its evidence text."""
    evidence_lower = evidence.lower()
    for fp in FAILURE_PATTERNS:
        if re.search(fp["pattern"], evidence_lower):
            return fp["category"], fp["suggestion"]
    return "unknown", "Review the failure evidence and fix manually."


def load_test_results(workspace_path, iteration=None):
    """Load test-results.json from workspace, finding latest iteration if not specified."""
    workspace = Path(workspace_path)

    if iteration:
        results_path = workspace / f"iteration-{iteration}" / "test-results.json"
        if results_path.exists():
            with open(results_path) as f:
                return json.load(f)
        return None

    # Find latest iteration
    latest = None
    latest_num = 0
    for d in workspace.iterdir():
        if d.is_dir() and d.name.startswith("iteration-"):
            try:
                num = int(d.name.split("-")[1])
            except (IndexError, ValueError):
                continue
            rp = d / "test-results.json"
            if rp.exists() and num > latest_num:
                latest_num = num
                latest = rp

    if latest:
        with open(latest) as f:
            return json.load(f)
    return None


def scan_agent_files(agent_path):
    """Scan agent directory and return file inventory."""
    agent_path = Path(agent_path)
    files = {}
    if not agent_path.exists():
        return files

    for f in agent_path.rglob("*"):
        if f.is_file() and not f.name.startswith("."):
            rel = str(f.relative_to(agent_path))
            try:
                content = f.read_text(errors="replace")
                files[rel] = {
                    "lines": len(content.splitlines()),
                    "size": f.stat().st_size,
                }
            except OSError:
                files[rel] = {"lines": 0, "size": 0}

    return files


def analyze_failures(test_results, agent_path):
    """Analyze test failures and produce correction plan."""
    failures = []
    agent_files = scan_agent_files(agent_path)

    for result in test_results.get("results", []):
        if result.get("passed") is True:
            continue

        for exp in result.get("expectations", []):
            if exp.get("verdict") == "FAIL":
                evidence = exp.get("evidence", "")
                category, suggestion = classify_failure(evidence)

                # Try to map failure to specific file
                affected_file = "SKILL.md"  # default
                evidence_lower = evidence.lower()
                for fname in agent_files:
                    if fname.lower() in evidence_lower or Path(fname).stem.lower() in evidence_lower:
                        affected_file = fname
                        break
                if "script" in evidence_lower:
                    script_files = [f for f in agent_files if f.startswith("scripts/")]
                    if script_files:
                        affected_file = script_files[0]

                failures.append({
                    "eval_id": result.get("eval_id"),
                    "eval_name": result.get("eval_name", ""),
                    "expectation": exp.get("text", ""),
                    "evidence": evidence,
                    "category": category,
                    "suggestion": suggestion,
                    "affected_file": affected_file,
                })

    # Group by file
    corrections_by_file = {}
    for f in failures:
        fname = f["affected_file"]
        if fname not in corrections_by_file:
            corrections_by_file[fname] = []
        corrections_by_file[fname].append(f)

    # Build correction plan
    plan = {
        "total_failures": len(failures),
        "categories": {},
        "corrections": [],
    }

    # Count by category
    for f in failures:
        cat = f["category"]
        plan["categories"][cat] = plan["categories"].get(cat, 0) + 1

    # Build per-file corrections
    for fname, file_failures in corrections_by_file.items():
        correction = {
            "file": fname,
            "failure_count": len(file_failures),
            "issues": [],
            "suggested_actions": [],
        }

        seen_suggestions = set()
        for ff in file_failures:
            correction["issues"].append({
                "eval_id": ff["eval_id"],
                "expectation": ff["expectation"],
                "evidence": ff["evidence"],
                "category": ff["category"],
            })
            if ff["suggestion"] not in seen_suggestions:
                correction["suggested_actions"].append(ff["suggestion"])
                seen_suggestions.add(ff["suggestion"])

        plan["corrections"].append(correction)

    # Sort by failure count (most problematic files first)
    plan["corrections"].sort(key=lambda c: c["failure_count"], reverse=True)

    return plan


def format_plan_human(plan):
    """Format correction plan for human reading."""
    lines = []
    lines.append(f"=== Auto-Correction Analysis ===")
    lines.append(f"Total failures: {plan['total_failures']}")
    lines.append("")

    if plan["categories"]:
        lines.append("Failure categories:")
        for cat, count in sorted(plan["categories"].items(), key=lambda x: -x[1]):
            lines.append(f"  {cat}: {count}")
        lines.append("")

    for correction in plan["corrections"]:
        lines.append(f"--- {correction['file']} ({correction['failure_count']} failures) ---")
        for issue in correction["issues"]:
            lines.append(f"  [{issue['category']}] eval-{issue['eval_id']}: {issue['expectation']}")
            if issue["evidence"]:
                lines.append(f"    Evidence: {issue['evidence'][:120]}...")
        lines.append("  Suggested actions:")
        for action in correction["suggested_actions"]:
            lines.append(f"    -> {action}")
        lines.append("")

    if not plan["corrections"]:
        lines.append("No failures found. All tests passed!")

    return "\n".join(lines)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Analyze test failures and suggest corrections")
    parser.add_argument("agent_path", help="Path to the agent directory")
    parser.add_argument("workspace_path", help="Path to the workspace directory")
    parser.add_argument("--iteration", type=int, default=None, help="Iteration number (latest if omitted)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    if not Path(args.agent_path).exists():
        print(f"ERROR: Agent not found: {args.agent_path}", file=sys.stderr)
        sys.exit(1)

    results = load_test_results(args.workspace_path, args.iteration)
    if not results:
        print("ERROR: No test results found.", file=sys.stderr)
        sys.exit(1)

    plan = analyze_failures(results, args.agent_path)

    if args.json:
        print(json.dumps(plan, indent=2, ensure_ascii=False))
    else:
        print(format_plan_human(plan))

    # Exit 0 if no failures, 1 if there are failures to fix
    sys.exit(0 if plan["total_failures"] == 0 else 1)


if __name__ == "__main__":
    main()
