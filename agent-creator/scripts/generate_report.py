#!/usr/bin/env python3
"""
Generate an HTML report for a created agent.

Reads context.json and test-results.json from the workspace,
populates the agent-report.html template, and writes the final report.

Usage:
    python generate_report.py <workspace-path> [--output report.html]
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def find_template():
    """Find the agent-report.html template."""
    script_dir = Path(__file__).parent.parent
    template_path = script_dir / 'assets' / 'agent-report.html'
    if template_path.exists():
        return template_path
    return None


def load_context(workspace_path):
    """Load context.json from workspace."""
    ctx_path = Path(workspace_path) / 'context.json'
    if ctx_path.exists():
        with open(ctx_path) as f:
            return json.load(f)
    return {}


def find_latest_test_results(workspace_path):
    """Find the most recent test-results.json in workspace iterations."""
    workspace = Path(workspace_path)
    latest = None
    latest_iteration = 0

    for d in workspace.iterdir():
        if d.is_dir() and d.name.startswith('iteration-'):
            try:
                iteration_num = int(d.name.split('-')[1])
            except (IndexError, ValueError):
                continue
            results_path = d / 'test-results.json'
            if results_path.exists() and iteration_num > latest_iteration:
                latest_iteration = iteration_num
                latest = results_path

    if latest:
        with open(latest) as f:
            return json.load(f)
    return {}


def generate_file_list_html(files):
    """Generate HTML list items for created files."""
    if not files:
        return '<li>No files recorded</li>'
    return '\n'.join(f'                <li>{f}</li>' for f in files)


def generate_test_results_html(results):
    """Generate HTML for test results."""
    if not results or 'results' not in results:
        return '<p>No test results available</p>'

    html_parts = []
    for r in results['results']:
        eval_name = r.get('eval_name', f"eval-{r.get('eval_id', '?')}")
        passed = r.get('passed')

        if passed is True:
            badge = '<span class="badge badge-success">PASS</span>'
        elif passed is False:
            badge = '<span class="badge badge-fail">FAIL</span>'
        else:
            badge = '<span class="badge badge-info">PENDING</span>'

        html_parts.append(
            f'            <div class="test-row">'
            f'<span class="test-name">{eval_name}</span>{badge}</div>'
        )

    return '\n'.join(html_parts)


def generate_corrections_html(corrections):
    """Generate HTML for corrections applied."""
    if not corrections:
        return '<p>No corrections were needed</p>'

    html_parts = []
    for c in corrections:
        iteration = c.get('iteration', '?')
        file_name = c.get('file', 'unknown')
        issue = c.get('issue', 'No description')
        fix = c.get('fix', 'No description')

        html_parts.append(
            f'            <div class="correction">'
            f'<span class="correction-file">Iteration {iteration} - {file_name}</span>'
            f'<p><strong>Issue:</strong> {issue}</p>'
            f'<p><strong>Fix:</strong> {fix}</p></div>'
        )

    return '\n'.join(html_parts)


def generate_report(workspace_path, output_path=None):
    """Generate the full HTML report.

    Args:
        workspace_path: Path to the agent workspace directory
        output_path: Optional output file path (defaults to workspace/report.html)

    Returns:
        Path to the generated report, or None on error
    """
    template_path = find_template()
    if not template_path:
        print("ERROR: agent-report.html template not found in assets/")
        return None

    template = template_path.read_text()
    context = load_context(workspace_path)
    test_results = find_latest_test_results(workspace_path)

    # Extract data from context
    agent_name = context.get('agent_name', 'Unknown Agent')
    requirements = context.get('requirements', {})
    description = requirements.get('purpose', 'No description available')
    triggers = requirements.get('triggers', [])
    created_files = context.get('created_files', [])
    corrections = context.get('corrections', [])
    test_history = context.get('test_history', [])

    # Calculate stats
    summary = test_results.get('summary', {})
    tests_passed = summary.get('passed', 0)
    tests_total = summary.get('total', 0)
    iterations = len(test_history) if test_history else (
        test_results.get('iteration', 0)
    )

    # Populate template
    html = template
    replacements = {
        '{{AGENT_NAME}}': agent_name,
        '{{AGENT_DESCRIPTION}}': description,
        '{{TESTS_PASSED}}': str(tests_passed),
        '{{TESTS_TOTAL}}': str(tests_total),
        '{{ITERATIONS}}': str(iterations),
        '{{CORRECTIONS}}': str(len(corrections)),
        '{{FILES_COUNT}}': str(len(created_files)),
        '{{FILE_LIST}}': generate_file_list_html(created_files),
        '{{TEST_RESULTS}}': generate_test_results_html(test_results),
        '{{CORRECTIONS_LIST}}': generate_corrections_html(corrections),
        '{{TRIGGERS}}': ', '.join(triggers) if triggers else 'N/A',
        '{{EXAMPLE_PROMPT}}': triggers[0] if triggers else 'N/A',
        '{{TIMESTAMP}}': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'),
    }

    for placeholder, value in replacements.items():
        html = html.replace(placeholder, value)

    # Write output
    if output_path is None:
        output_path = Path(workspace_path) / 'report.html'
    else:
        output_path = Path(output_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html)
    print(f"Report generated: {output_path}")
    return output_path


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Generate agent report')
    parser.add_argument('workspace_path', help='Path to the agent workspace')
    parser.add_argument('--output', '-o', help='Output file path')
    args = parser.parse_args()

    if not Path(args.workspace_path).exists():
        print(f"ERROR: Workspace not found: {args.workspace_path}")
        sys.exit(1)

    result = generate_report(args.workspace_path, args.output)
    sys.exit(0 if result else 1)


if __name__ == "__main__":
    main()
