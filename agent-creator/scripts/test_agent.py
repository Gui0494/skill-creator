#!/usr/bin/env python3
"""
Automated testing script for agents created by agent-creator.

Reads evals.json, executes each test case using `claude -p` with and
without the agent's skill, collects outputs and timing, and writes
test-results.json.

Follows the same subprocess patterns as skill-creator/scripts/run_eval.py:
- Creates temporary command files in .claude/commands/
- Removes CLAUDECODE env var for safe nesting
- Supports resume (skips already-completed evals)

Usage:
    python test_agent.py <agent-path> <workspace-path> [--iteration N] [--resume]
"""

import json
import os
import re
import subprocess
import sys
import time
import uuid
from pathlib import Path
from datetime import datetime, timezone


def find_project_root():
    """Find project root by walking up from cwd looking for .claude/."""
    current = Path.cwd()
    for parent in [current, *current.parents]:
        if (parent / ".claude").is_dir():
            return parent
    return current


def load_evals(workspace_path):
    """Load evals.json from workspace."""
    evals_path = Path(workspace_path) / 'evals' / 'evals.json'
    if not evals_path.exists():
        print(f"ERROR: evals.json not found at {evals_path}", file=sys.stderr)
        sys.exit(1)
    with open(evals_path) as f:
        return json.load(f)


def parse_skill_name_desc(skill_path):
    """Parse name and description from a skill's SKILL.md without PyYAML."""
    skill_md = Path(skill_path) / 'SKILL.md'
    if not skill_md.exists():
        return None, None

    content = skill_md.read_text()
    match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not match:
        return None, None

    name = None
    description = None
    for line in match.group(1).split('\n'):
        if line.startswith('name:'):
            name = line.split(':', 1)[1].strip()
        elif line.startswith('description:'):
            description = line.split(':', 1)[1].strip()

    return name, description


def create_temp_command(skill_name, skill_description, project_root):
    """Create a temporary command file in .claude/commands/ for skill testing.

    Returns (command_file_path, clean_name) for cleanup.
    """
    unique_id = uuid.uuid4().hex[:8]
    clean_name = f"{skill_name}-test-{unique_id}"
    commands_dir = Path(project_root) / ".claude" / "commands"
    commands_dir.mkdir(parents=True, exist_ok=True)

    command_file = commands_dir / f"{clean_name}.md"
    indented_desc = "\n  ".join(skill_description.split("\n"))
    command_content = (
        f"---\n"
        f"description: |\n"
        f"  {indented_desc}\n"
        f"---\n\n"
        f"# {skill_name}\n\n"
        f"This skill handles: {skill_description}\n"
    )
    command_file.write_text(command_content)
    return command_file, clean_name


def get_clean_env():
    """Get environment with CLAUDECODE removed for safe subprocess nesting."""
    return {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}


def run_claude(prompt, output_dir, skill_path=None, project_root=None, timeout=300):
    """Execute claude -p and capture results.

    If skill_path is provided, creates a temporary command file so Claude
    discovers the skill. Follows run_eval.py patterns for subprocess handling.

    Returns dict with success, stdout, stderr, duration_ms, transcript_path.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if project_root is None:
        project_root = str(find_project_root())

    command_file = None
    env = get_clean_env()

    try:
        # If skill provided, create temp command for Claude to discover
        if skill_path:
            skill_name, skill_desc = parse_skill_name_desc(skill_path)
            if skill_name and skill_desc:
                command_file, _ = create_temp_command(skill_name, skill_desc, project_root)

        cmd = ["claude", "-p", prompt, "--output-format", "text"]

        start_time = time.time()
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=project_root,
            env=env,
        )
        duration_ms = int((time.time() - start_time) * 1000)

        # Save transcript
        transcript_path = output_dir / 'transcript.md'
        transcript = f"# Execution Transcript\n\n"
        transcript += f"**Prompt:** {prompt}\n\n"
        transcript += f"**Skill:** {skill_path or 'none (baseline)'}\n\n"
        transcript += f"**Duration:** {duration_ms}ms\n\n"
        transcript += f"**Exit code:** {result.returncode}\n\n"
        transcript += f"## Output\n\n```\n{result.stdout}\n```\n\n"
        if result.stderr:
            transcript += f"## Errors\n\n```\n{result.stderr}\n```\n"
        transcript_path.write_text(transcript)

        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "duration_ms": duration_ms,
            "transcript_path": str(transcript_path),
        }

    except subprocess.TimeoutExpired:
        duration_ms = int((time.time() - start_time) * 1000)
        return {
            "success": False,
            "stdout": "",
            "stderr": f"TIMEOUT: Execution exceeded {timeout} seconds",
            "duration_ms": duration_ms,
            "transcript_path": None,
        }

    except FileNotFoundError:
        return {
            "success": False,
            "stdout": "",
            "stderr": "ERROR: 'claude' command not found. Run preflight.py first.",
            "duration_ms": 0,
            "transcript_path": None,
        }

    finally:
        # Cleanup temporary command file
        if command_file and command_file.exists():
            try:
                command_file.unlink()
            except OSError:
                pass


def is_eval_complete(iteration_dir, eval_id):
    """Check if an eval already has results (for resume support)."""
    eval_dir = Path(iteration_dir) / f'eval-{eval_id}'
    with_transcript = eval_dir / 'with_skill' / 'outputs' / 'transcript.md'
    without_transcript = eval_dir / 'without_skill' / 'outputs' / 'transcript.md'
    return with_transcript.exists() and without_transcript.exists()


def run_tests(agent_path, workspace_path, iteration=1, resume=False):
    """Run all test cases and collect results.

    Args:
        agent_path: Path to the agent skill directory
        workspace_path: Path to the agent workspace
        iteration: Iteration number
        resume: If True, skip evals that already have results
    """
    evals_data = load_evals(workspace_path)
    agent_path = Path(agent_path).resolve()
    workspace_path = Path(workspace_path)
    project_root = str(find_project_root())

    iteration_dir = workspace_path / f'iteration-{iteration}'
    iteration_dir.mkdir(parents=True, exist_ok=True)

    # Load existing results if resuming
    results_path = iteration_dir / 'test-results.json'
    existing_results = {}
    if resume and results_path.exists():
        with open(results_path) as f:
            existing_data = json.load(f)
            for r in existing_data.get('results', []):
                existing_results[r['eval_id']] = r

    results = []
    skipped = 0

    for eval_case in evals_data.get('evals', []):
        eval_id = eval_case['id']
        prompt = eval_case['prompt']
        files = eval_case.get('files', [])
        expectations = eval_case.get('expectations', [])
        expected_output = eval_case.get('expected_output', '')

        # Resume: skip completed evals
        if resume and eval_id in existing_results and is_eval_complete(iteration_dir, eval_id):
            print(f"  [SKIP] eval-{eval_id}: already complete")
            results.append(existing_results[eval_id])
            skipped += 1
            continue

        eval_dir = iteration_dir / f'eval-{eval_id}'

        # Add file context to prompt
        full_prompt = prompt
        if files:
            file_context = "\n".join(f"Input file: {f}" for f in files)
            full_prompt = f"{file_context}\n\n{prompt}"

        print(f"\n--- eval-{eval_id}: {prompt[:60]}... ---")

        # Run with skill
        print(f"  [RUN] with skill...")
        with_skill_dir = eval_dir / 'with_skill' / 'outputs'
        with_result = run_claude(
            full_prompt, with_skill_dir,
            skill_path=str(agent_path),
            project_root=project_root,
        )

        # Run baseline (without skill)
        print(f"  [RUN] baseline (without skill)...")
        without_skill_dir = eval_dir / 'without_skill' / 'outputs'
        without_result = run_claude(
            full_prompt, without_skill_dir,
            project_root=project_root,
        )

        result = {
            "eval_id": eval_id,
            "eval_name": expected_output[:80] if expected_output else f"eval-{eval_id}",
            "prompt": prompt,
            "with_skill": {
                "success": with_result["success"],
                "duration_ms": with_result["duration_ms"],
                "transcript_path": with_result["transcript_path"],
            },
            "without_skill": {
                "success": without_result["success"],
                "duration_ms": without_result["duration_ms"],
                "transcript_path": without_result["transcript_path"],
            },
            "expectations": [
                {"text": exp, "verdict": "PENDING", "evidence": ""}
                for exp in expectations
            ],
            "passed": None,
        }
        results.append(result)

    # Write results
    test_results = {
        "iteration": iteration,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent_name": evals_data.get('skill_name', 'unknown'),
        "agent_path": str(agent_path),
        "results": results,
        "summary": {
            "total": len(results),
            "executed": len(results) - skipped,
            "skipped": skipped,
            "pending_grading": len(results),
        },
    }

    with open(results_path, 'w') as f:
        json.dump(test_results, f, indent=2, ensure_ascii=False)

    print(f"\nResults saved to: {results_path}")
    print(f"Total: {len(results)} | Executed: {len(results) - skipped} | Skipped: {skipped}")
    print(f"Pending grading: {len(results)} (use agent-tester subagent)")

    return test_results


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Test a created agent')
    parser.add_argument('agent_path', help='Path to the agent directory')
    parser.add_argument('workspace_path', help='Path to the workspace directory')
    parser.add_argument('--iteration', type=int, default=1, help='Iteration number')
    parser.add_argument('--resume', action='store_true',
                        help='Skip evals that already have results')
    args = parser.parse_args()

    if not Path(args.agent_path).exists():
        print(f"ERROR: Agent not found: {args.agent_path}", file=sys.stderr)
        sys.exit(1)

    if not Path(args.workspace_path).exists():
        print(f"ERROR: Workspace not found: {args.workspace_path}", file=sys.stderr)
        sys.exit(1)

    run_tests(args.agent_path, args.workspace_path, args.iteration, args.resume)


if __name__ == "__main__":
    main()
