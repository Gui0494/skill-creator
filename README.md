```
🟦🟦🟦🟦          🟦🟦🟦🟦🟦🟦          🟦🟦🟦🟦🟦🟦          🟦🟦🟦🟦🟦🟦          🟦🟦🟦🟦          🟦🟦🟦🟦          🟦🟦🟦🟦🟦🟦
🟦🟦🟦🟦🟦🟦        🟦🟦    🟦🟦          🟦🟦    🟦🟦          🟦🟦                    🟦🟦  🟦🟦        🟦🟦🟦🟦            🟦🟦
🟦🟦  🟦🟦        🟦🟦    🟦🟦          🟦🟦🟦🟦🟦🟦          🟦🟦🟦🟦                  🟦🟦🟦🟦        🟦🟦  🟦🟦            🟦🟦
🟦🟦🟦🟦🟦🟦        🟦🟦    🟦🟦          🟦🟦  🟦🟦            🟦🟦                    🟦🟦  🟦🟦      🟦🟦🟦🟦🟦🟦            🟦🟦
🟦🟦  🟦🟦          🟦🟦🟦🟦🟦🟦          🟦🟦    🟦🟦          🟦🟦🟦🟦🟦🟦          🟦🟦    🟦🟦      🟦🟦  🟦🟦          🟦🟦🟦🟦🟦🟦
```

**Meta-agent system that creates, tests, and delivers production-ready agents.**

Zero external dependencies. Python 3.8+. Works with any CLI (Python, Node.js).

---

## What is this?

AurexAI is a two-part system:

| Component | Purpose |
|-----------|---------|
| **skill-creator/** | Create and improve Claude Code skills with iterative testing |
| **agent-creator/** | Meta-agent that creates other agents end-to-end (requirements, generation, testing, auto-correction, delivery) |

The agent-creator can be called by an external CLI when a skill/agent is missing. Example: user asks "design me a landing page" but no design agent exists — your CLI calls agent-creator, which creates one automatically.

## Quickstart

```bash
# 1. Check environment
python3 agent-creator/scripts/preflight.py

# 2. Create an agent via CLI bridge
echo '{
  "action": "create",
  "agent_name": "code-reviewer",
  "requirements": {
    "purpose": "Review Python code and suggest improvements",
    "triggers": ["review", "code review"],
    "tools": ["Read", "Grep", "Glob"]
  }
}' | python3 agent-creator/scripts/cli_bridge.py --create

# 3. Validate the created agent
python3 agent-creator/scripts/validate_agent.py ./code-reviewer
```

## Project Structure

```
aurexai/
├── skill-creator/                   # Skill creation & improvement
│   ├── SKILL.md                     # Main skill definition
│   ├── agents/                      # Subagents (grader, comparator, analyzer)
│   ├── scripts/                     # Python tools (run_eval, benchmark, package)
│   ├── references/                  # JSON schemas
│   ├── eval-viewer/                 # Interactive HTML result viewer
│   └── assets/                      # HTML templates
│
├── agent-creator/                   # Meta-agent: creates other agents
│   ├── SKILL.md                     # 6-phase workflow definition
│   ├── agents/
│   │   └── agent-tester.md          # Subagent for grading test results
│   ├── scripts/
│   │   ├── cli_bridge.py            # CLI entry point (JSON stdin/stdout)
│   │   ├── validate_agent.py        # Structure validation
│   │   ├── test_agent.py            # Automated testing with resume
│   │   ├── auto_correct.py          # Failure analysis & correction plans
│   │   ├── preflight.py             # Environment checks
│   │   └── generate_report.py       # HTML report generation
│   ├── references/
│   │   ├── agent-template.md        # Template & quality checklist
│   │   ├── schemas.md               # JSON schemas (context, results)
│   │   └── cli-protocol.md          # CLI integration protocol docs
│   ├── assets/
│   │   ├── agent-report.html        # Dark theme report template
│   │   └── logo.txt                 # AurexAI logo
│   └── tests/
│       └── test_scripts.py          # Unit tests
│
├── requirements.txt                 # Dependencies (none - stdlib only)
└── README.md
```

## Agent Creator: 6-Phase Workflow

```
Phase 1: Requirements    Capture what the agent should do
Phase 2: Generation      Create SKILL.md + supporting files
Phase 3: Test Cases      Generate 3-5 realistic test scenarios
Phase 4: Validation      Run tests (with/without skill baseline)
Phase 5: Auto-Correct    Analyze failures, fix, re-test (max 3 iterations)
Phase 6: Delivery        Validate, generate report, package
```

## CLI Bridge

The `cli_bridge.py` enables any external tool to create agents programmatically.

### Python

```python
import subprocess, json

result = subprocess.run(
    ["python3", "agent-creator/scripts/cli_bridge.py", "--create"],
    input=json.dumps({
        "agent_name": "design-agent",
        "requirements": {"purpose": "Create professional web designs"},
        "options": {"auto_test": True, "output_dir": "./agents"}
    }),
    capture_output=True, text=True
)
response = json.loads(result.stdout)
print(f"Agent: {response['agent_path']} | Tests: {response['test_results']}")
```

### Node.js

```javascript
const { execSync } = require('child_process');
const result = execSync('python3 agent-creator/scripts/cli_bridge.py --create', {
    input: JSON.stringify({
        agent_name: 'design-agent',
        requirements: { purpose: 'Create professional web designs' },
        options: { auto_test: true, output_dir: './agents' }
    })
});
console.log(JSON.parse(result.toString()));
```

### Actions

| Flag | Action | Description |
|------|--------|-------------|
| `--create` | Full workflow | Creates agent through all 6 phases |
| `--validate` | Structure check | Validates SKILL.md, frontmatter, files |
| `--test` | Run tests | Executes evals with resume support |
| `--analyze` | Failure analysis | Classifies failures, suggests corrections |
| `--status` | Check progress | Reads context.json from workspace |
| `--report` | Generate report | Creates HTML report from results |
| `--preflight` | Environment check | Verifies Python, Claude CLI, disk, perms |

## Scripts

| Script | Usage |
|--------|-------|
| `preflight.py` | `python3 agent-creator/scripts/preflight.py` |
| `validate_agent.py` | `python3 agent-creator/scripts/validate_agent.py <agent-dir>` |
| `test_agent.py` | `python3 agent-creator/scripts/test_agent.py <agent> <workspace> --resume` |
| `auto_correct.py` | `python3 agent-creator/scripts/auto_correct.py <agent> <workspace>` |
| `generate_report.py` | `python3 agent-creator/scripts/generate_report.py <workspace>` |
| `cli_bridge.py` | `echo '{"action":"..."}' \| python3 agent-creator/scripts/cli_bridge.py --<action>` |

## Running Tests

```bash
python3 agent-creator/tests/test_scripts.py
```

## Requirements

- Python 3.8+
- Claude CLI (for agent testing phases)
- No external Python packages required

## License

See [LICENSE.txt](skill-creator/LICENSE.txt)
