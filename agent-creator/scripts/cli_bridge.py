#!/usr/bin/env python3
"""
CLI Bridge - Entry point for external CLI integration.

This script serves as the programmatic interface between external CLI tools
(Python subprocess, Node.js child_process) and the agent-creator skill.

Communication protocol:
- Input: JSON via stdin
- Output: JSON via stdout
- Errors: stderr (human-readable)
- Exit codes: 0=success, 1=error, 2=partial (some phases failed)

Actions:
  --create    Full agent creation workflow (phases 1-6)
  --validate  Validate an existing agent structure
  --test      Run tests on an existing agent
  --analyze   Analyze test failures and suggest corrections
  --status    Read context.json status of an in-progress creation
  --preflight Check environment readiness
  --report    Generate HTML report from workspace

Usage from Python:
    import subprocess, json
    result = subprocess.run(
        ["python3", "agent-creator/scripts/cli_bridge.py", "--create"],
        input=json.dumps(request), capture_output=True, text=True
    )
    response = json.loads(result.stdout)

Usage from Node.js:
    const { execSync } = require('child_process');
    const result = execSync(
        'python3 agent-creator/scripts/cli_bridge.py --validate',
        { input: JSON.stringify(request) }
    );
    const response = JSON.parse(result.toString());

See references/cli-protocol.md for full protocol documentation.
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


# Ensure sibling scripts are importable regardless of invocation path
SCRIPT_DIR = Path(__file__).parent.resolve()
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
AGENT_CREATOR_DIR = SCRIPT_DIR.parent


def log(msg):
    """Log to stderr (never pollutes JSON stdout)."""
    print(f"[agent-creator] {msg}", file=sys.stderr)


def read_request():
    """Read JSON request from stdin."""
    if sys.stdin.isatty():
        return {}
    try:
        raw = sys.stdin.read().strip()
        if not raw:
            return {}
        return json.loads(raw)
    except json.JSONDecodeError as e:
        return {"_error": f"Invalid JSON input: {e}"}


def respond(data, exit_code=0):
    """Write JSON response to stdout and exit."""
    print(json.dumps(data, indent=2, ensure_ascii=False))
    sys.exit(exit_code)


def error_response(message, code="ERROR", exit_code=1):
    """Send error response."""
    respond({
        "status": "error",
        "error": {"code": code, "message": message},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }, exit_code)


# ─── Action: preflight ──────────────────────────────────────────────

def action_preflight(request):
    """Run preflight environment checks."""
    from preflight import run_preflight

    output_dir = request.get("options", {}).get("output_dir")
    result = run_preflight(output_dir, as_json=False)

    respond({
        "status": "success" if result["passed"] else "failed",
        "action": "preflight",
        "checks": result["checks"],
        "summary": result["summary"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }, 0 if result["passed"] else 1)


# ─── Action: validate ───────────────────────────────────────────────

def action_validate(request):
    """Validate an agent's structure."""
    from validate_agent import validate_agent

    agent_path = request.get("agent_path")
    if not agent_path:
        error_response("Missing 'agent_path' in request", "MISSING_PARAM")

    agent_path = Path(agent_path)
    if not agent_path.exists():
        error_response(f"Agent not found: {agent_path}", "NOT_FOUND")

    is_valid, message = validate_agent(agent_path)

    respond({
        "status": "success" if is_valid else "failed",
        "action": "validate",
        "valid": is_valid,
        "message": message,
        "agent_path": str(agent_path),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }, 0 if is_valid else 1)


# ─── Action: test ───────────────────────────────────────────────────

def action_test(request):
    """Run tests on an existing agent."""
    from test_agent import run_tests

    agent_path = request.get("agent_path")
    workspace_path = request.get("workspace_path")

    if not agent_path:
        error_response("Missing 'agent_path' in request", "MISSING_PARAM")
    if not workspace_path:
        error_response("Missing 'workspace_path' in request", "MISSING_PARAM")

    options = request.get("options", {})
    iteration = options.get("iteration", 1)
    resume = options.get("resume", False)

    log(f"Testing agent: {agent_path}")
    log(f"Workspace: {workspace_path}")
    log(f"Iteration: {iteration}, Resume: {resume}")

    results = run_tests(agent_path, workspace_path, iteration, resume)

    respond({
        "status": "success",
        "action": "test",
        "agent_path": str(agent_path),
        "workspace_path": str(workspace_path),
        "iteration": iteration,
        "results": results,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


# ─── Action: status ─────────────────────────────────────────────────

def action_status(request):
    """Read context.json status from a workspace."""
    workspace_path = request.get("workspace_path")
    if not workspace_path:
        # Try to find by agent name
        agent_name = request.get("agent_name")
        if agent_name:
            workspace_path = f"{agent_name}-workspace"

    if not workspace_path:
        error_response("Missing 'workspace_path' or 'agent_name' in request", "MISSING_PARAM")

    ctx_path = Path(workspace_path) / 'context.json'
    if not ctx_path.exists():
        respond({
            "status": "not_found",
            "action": "status",
            "message": f"No context.json found at {ctx_path}",
            "workspace_path": str(workspace_path),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return

    with open(ctx_path) as f:
        context = json.load(f)

    respond({
        "status": "success",
        "action": "status",
        "context": context,
        "workspace_path": str(workspace_path),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


# ─── Action: report ─────────────────────────────────────────────────

def action_report(request):
    """Generate HTML report from workspace."""
    from generate_report import generate_report

    workspace_path = request.get("workspace_path")
    if not workspace_path:
        error_response("Missing 'workspace_path' in request", "MISSING_PARAM")

    output_path = request.get("output_path")

    report_path = generate_report(workspace_path, output_path)
    if report_path:
        respond({
            "status": "success",
            "action": "report",
            "report_path": str(report_path),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    else:
        error_response("Failed to generate report", "REPORT_FAILED")


# ─── Action: analyze ────────────────────────────────────────────────

def action_analyze(request):
    """Analyze test failures and suggest corrections."""
    from auto_correct import analyze_failures, load_test_results

    agent_path = request.get("agent_path")
    workspace_path = request.get("workspace_path")

    if not agent_path:
        error_response("Missing 'agent_path' in request", "MISSING_PARAM")
    if not workspace_path:
        error_response("Missing 'workspace_path' in request", "MISSING_PARAM")

    options = request.get("options", {})
    iteration = options.get("iteration")

    results = load_test_results(workspace_path, iteration)
    if not results:
        error_response("No test results found in workspace", "NOT_FOUND")

    plan = analyze_failures(results, agent_path)

    respond({
        "status": "success",
        "action": "analyze",
        "agent_path": str(agent_path),
        "workspace_path": str(workspace_path),
        "total_failures": plan["total_failures"],
        "categories": plan["categories"],
        "corrections": plan["corrections"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


# ─── Action: create ─────────────────────────────────────────────────

def action_create(request):
    """Orchestrate the full agent creation workflow.

    This action invokes Claude to perform the actual agent creation,
    passing the requirements as context. The CLI bridge sets up the
    workspace, passes requirements to Claude, and monitors the process.

    For fully automated creation, Claude handles phases 1-6 using
    the agent-creator SKILL.md instructions.
    """
    agent_name = request.get("agent_name")
    requirements = request.get("requirements", {})
    options = request.get("options", {})

    if not agent_name:
        error_response("Missing 'agent_name' in request", "MISSING_PARAM")
    if not requirements:
        error_response("Missing 'requirements' in request", "MISSING_PARAM")

    output_dir = Path(options.get("output_dir", "."))
    agent_path = output_dir / agent_name
    workspace_path = output_dir / f"{agent_name}-workspace"

    # Create workspace and save initial context
    workspace_path.mkdir(parents=True, exist_ok=True)
    (workspace_path / "evals").mkdir(exist_ok=True)

    context = {
        "agent_name": agent_name,
        "status": "requirements",
        "phase": 1,
        "requirements": requirements,
        "created_files": [],
        "test_history": [],
        "corrections": [],
        "options": options,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    ctx_path = workspace_path / "context.json"
    with open(ctx_path, 'w') as f:
        json.dump(context, f, indent=2, ensure_ascii=False)

    log(f"Workspace created: {workspace_path}")
    log(f"Context saved: {ctx_path}")

    # Build the prompt for Claude to create the agent
    prompt_parts = [
        f"Create an agent called '{agent_name}' with these requirements:",
        f"",
        f"Purpose: {requirements.get('purpose', 'Not specified')}",
    ]

    if requirements.get('triggers'):
        prompt_parts.append(f"Triggers: {', '.join(requirements['triggers'])}")
    if requirements.get('tools'):
        prompt_parts.append(f"Tools needed: {', '.join(requirements['tools'])}")
    if requirements.get('output_format'):
        prompt_parts.append(f"Output format: {requirements['output_format']}")
    if requirements.get('edge_cases'):
        prompt_parts.append(f"Edge cases: {', '.join(requirements['edge_cases'])}")
    if requirements.get('example_scenario'):
        prompt_parts.append(f"Example scenario: {requirements['example_scenario']}")

    prompt_parts.extend([
        f"",
        f"Create the agent at: {agent_path}",
        f"Workspace at: {workspace_path}",
        f"",
        f"Follow the agent-creator workflow (all 6 phases).",
        f"Use the skill-creator skill to create the skill.",
        f"Create test cases, run tests, self-correct if needed.",
        f"Update {ctx_path} with progress after each phase.",
    ])

    auto_test = options.get("auto_test", True)
    max_corrections = options.get("max_corrections", 3)
    if not auto_test:
        prompt_parts.append("Skip testing phases (4-5).")
    prompt_parts.append(f"Max self-correction iterations: {max_corrections}")

    full_prompt = "\n".join(prompt_parts)

    # Invoke Claude with the agent-creator skill
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}

    log("Invoking Claude to create the agent...")

    try:
        result = subprocess.run(
            ["claude", "-p", full_prompt, "--output-format", "text"],
            capture_output=True,
            text=True,
            timeout=600,
            env=env,
        )

        # Read final context for results
        if ctx_path.exists():
            with open(ctx_path) as f:
                final_context = json.load(f)
        else:
            final_context = context

        # Check what was actually created
        created_files = []
        if agent_path.exists():
            for f in agent_path.rglob('*'):
                if f.is_file():
                    created_files.append(str(f.relative_to(agent_path)))

        test_results = final_context.get('test_history', [{}])
        latest_test = test_results[-1] if test_results else {}

        response = {
            "status": "success" if result.returncode == 0 else "partial",
            "action": "create",
            "agent_name": agent_name,
            "agent_path": str(agent_path),
            "workspace_path": str(workspace_path),
            "phase_completed": final_context.get("phase", 1),
            "test_results": {
                "passed": latest_test.get("passed", 0),
                "failed": latest_test.get("failed", 0),
                "total": latest_test.get("total", 0),
            },
            "corrections_applied": len(final_context.get("corrections", [])),
            "files_created": created_files,
            "errors": [result.stderr] if result.stderr and result.returncode != 0 else [],
            "claude_output": result.stdout[:2000] if result.stdout else "",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        exit_code = 0 if result.returncode == 0 else 2
        respond(response, exit_code)

    except subprocess.TimeoutExpired:
        error_response("Agent creation timed out (600s limit)", "TIMEOUT")

    except FileNotFoundError:
        error_response(
            "'claude' command not found. Install Claude CLI first. "
            "Run with --preflight to check environment.",
            "CLAUDE_NOT_FOUND"
        )


# ─── Main dispatcher ────────────────────────────────────────────────

ACTIONS = {
    "create": action_create,
    "validate": action_validate,
    "test": action_test,
    "analyze": action_analyze,
    "status": action_status,
    "report": action_report,
    "preflight": action_preflight,
}


def main():
    parser = argparse.ArgumentParser(
        description='Agent Creator CLI Bridge',
        epilog='See references/cli-protocol.md for full documentation.'
    )

    action_group = parser.add_mutually_exclusive_group(required=True)
    action_group.add_argument('--create', action='store_const', const='create',
                              dest='action', help='Create a new agent (full workflow)')
    action_group.add_argument('--validate', action='store_const', const='validate',
                              dest='action', help='Validate an agent structure')
    action_group.add_argument('--test', action='store_const', const='test',
                              dest='action', help='Run tests on an agent')
    action_group.add_argument('--analyze', action='store_const', const='analyze',
                              dest='action', help='Analyze test failures')
    action_group.add_argument('--status', action='store_const', const='status',
                              dest='action', help='Check creation status')
    action_group.add_argument('--report', action='store_const', const='report',
                              dest='action', help='Generate HTML report')
    action_group.add_argument('--preflight', action='store_const', const='preflight',
                              dest='action', help='Check environment readiness')

    args = parser.parse_args()

    # Read request from stdin
    request = read_request()

    if "_error" in request:
        error_response(request["_error"], "INVALID_INPUT")

    # Also accept action from JSON body (overrides CLI flag)
    action = request.get("action", args.action)

    if action not in ACTIONS:
        error_response(f"Unknown action: {action}. Valid: {', '.join(ACTIONS.keys())}", "UNKNOWN_ACTION")

    # Execute action
    try:
        ACTIONS[action](request)
    except Exception as e:
        error_response(f"Unexpected error: {e}", "INTERNAL_ERROR")


if __name__ == "__main__":
    main()
