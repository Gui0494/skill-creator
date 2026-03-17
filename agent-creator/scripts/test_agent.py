#!/usr/bin/env python3
"""
Automated testing script for agents created by agent-creator.

Reads evals.json, executes each test case using `claude -p` with and
without the agent's skill, collects outputs and timing, and writes
test-results.json.

Usage:
    python test_agent.py <agent-path> <workspace-path> [--iteration N]
"""

import sys
import os
import json
import time
import subprocess
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timezone


def load_evals(workspace_path):
    """Load evals.json from workspace."""
    evals_path = Path(workspace_path) / 'evals' / 'evals.json'
    if not evals_path.exists():
        print(f"ERROR: evals.json not found at {evals_path}")
        sys.exit(1)

    with open(evals_path) as f:
        return json.load(f)


def run_claude_with_skill(prompt, skill_path, output_dir, files=None):
    """Execute claude -p with a skill and capture output."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Build the command
    cmd = ['claude', '-p', '--output-format', 'json']

    # Add skill as custom instructions via allowedTools
    skill_md = Path(skill_path) / 'SKILL.md'
    if skill_md.exists():
        cmd.extend(['--append-system-prompt', f'Use the skill at {skill_path}. Read {skill_md} for instructions.'])

    # Add file context if needed
    full_prompt = prompt
    if files:
        file_context = "\n".join(f"Input file: {f}" for f in files)
        full_prompt = f"{file_context}\n\n{prompt}"

    start_time = time.time()
    try:
        result = subprocess.run(
            cmd,
            input=full_prompt,
            capture_output=True,
            text=True,
            timeout=300,
            cwd=str(output_dir)
        )
        duration_ms = int((time.time() - start_time) * 1000)

        # Save transcript
        transcript_path = output_dir / 'transcript.md'
        transcript_content = f"# Execution Transcript\n\n"
        transcript_content += f"**Prompt:** {prompt}\n\n"
        transcript_content += f"**Duration:** {duration_ms}ms\n\n"
        transcript_content += f"**Exit code:** {result.returncode}\n\n"
        transcript_content += f"## stdout\n\n```\n{result.stdout}\n```\n\n"
        if result.stderr:
            transcript_content += f"## stderr\n\n```\n{result.stderr}\n```\n"
        transcript_path.write_text(transcript_content)

        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "duration_ms": duration_ms,
            "transcript_path": str(transcript_path)
        }
    except subprocess.TimeoutExpired:
        duration_ms = int((time.time() - start_time) * 1000)
        return {
            "success": False,
            "stdout": "",
            "stderr": "TIMEOUT: Execution exceeded 300 seconds",
            "duration_ms": duration_ms,
            "transcript_path": None
        }
    except FileNotFoundError:
        return {
            "success": False,
            "stdout": "",
            "stderr": "ERROR: 'claude' command not found. Is Claude CLI installed?",
            "duration_ms": 0,
            "transcript_path": None
        }


def run_tests(agent_path, workspace_path, iteration=1):
    """Run all test cases and collect results."""
    evals_data = load_evals(workspace_path)
    agent_path = Path(agent_path)
    workspace_path = Path(workspace_path)

    iteration_dir = workspace_path / f'iteration-{iteration}'
    iteration_dir.mkdir(parents=True, exist_ok=True)

    results = []

    for eval_case in evals_data.get('evals', []):
        eval_id = eval_case['id']
        prompt = eval_case['prompt']
        files = eval_case.get('files', [])
        expectations = eval_case.get('expectations', [])
        expected_output = eval_case.get('expected_output', '')

        eval_dir = iteration_dir / f'eval-{eval_id}'

        print(f"\n--- Running eval {eval_id}: {prompt[:60]}... ---")

        # Run with skill
        print(f"  Running with skill...")
        with_skill_dir = eval_dir / 'with_skill' / 'outputs'
        with_result = run_claude_with_skill(prompt, agent_path, with_skill_dir, files)

        # Run without skill (baseline)
        print(f"  Running baseline (without skill)...")
        without_skill_dir = eval_dir / 'without_skill' / 'outputs'
        without_result = run_claude_with_skill(prompt, '', without_skill_dir, files)

        result = {
            "eval_id": eval_id,
            "eval_name": expected_output[:80] if expected_output else f"eval-{eval_id}",
            "prompt": prompt,
            "with_skill": {
                "success": with_result["success"],
                "duration_ms": with_result["duration_ms"],
                "transcript_path": with_result["transcript_path"]
            },
            "without_skill": {
                "success": without_result["success"],
                "duration_ms": without_result["duration_ms"],
                "transcript_path": without_result["transcript_path"]
            },
            "expectations": [
                {"text": exp, "verdict": "PENDING", "evidence": ""}
                for exp in expectations
            ],
            "passed": None  # To be determined by grading
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
            "executed": len(results),
            "pending_grading": len(results)
        }
    }

    results_path = iteration_dir / 'test-results.json'
    with open(results_path, 'w') as f:
        json.dump(test_results, f, indent=2, ensure_ascii=False)

    print(f"\nResults saved to: {results_path}")
    print(f"Total evals: {len(results)}")
    print(f"Pending grading: {len(results)} (use agent-tester to grade)")

    return test_results


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Test a created agent')
    parser.add_argument('agent_path', help='Path to the agent directory')
    parser.add_argument('workspace_path', help='Path to the workspace directory')
    parser.add_argument('--iteration', type=int, default=1, help='Iteration number')

    args = parser.parse_args()

    if not Path(args.agent_path).exists():
        print(f"ERROR: Agent not found: {args.agent_path}")
        sys.exit(1)

    if not Path(args.workspace_path).exists():
        print(f"ERROR: Workspace not found: {args.workspace_path}")
        sys.exit(1)

    run_tests(args.agent_path, args.workspace_path, args.iteration)


if __name__ == "__main__":
    main()
