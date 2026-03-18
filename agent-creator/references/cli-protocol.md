# CLI Protocol - Agent Creator

Documentação do protocolo de comunicação entre CLIs externos e o agent-creator.

## Indice

1. [Visao Geral](#visao-geral)
2. [Actions](#actions)
3. [Request Schema](#request-schema)
4. [Response Schema](#response-schema)
5. [Codigos de Erro](#codigos-de-erro)
6. [Exemplos Python](#exemplos-python)
7. [Exemplos Node.js](#exemplos-nodejs)

---

## Visao Geral

O `cli_bridge.py` serve como ponte entre qualquer CLI externo e o agent-creator. A comunicacao usa JSON via stdin/stdout.

```
CLI (Python/Node.js)
  |
  |-- stdin: JSON request
  |-- stdout: JSON response
  |-- stderr: logs (human-readable)
  |-- exit code: 0=success, 1=error, 2=partial
  |
  v
cli_bridge.py --<action>
```

**Entry point:**
```bash
python3 agent-creator/scripts/cli_bridge.py --<action>
```

**Actions disponíveis:** `--create`, `--validate`, `--test`, `--analyze`, `--status`, `--report`, `--preflight`

---

## Actions

### --create

Cria um agente completo (fases 1-6). Invoca Claude para gerar o skill, testar e entregar.

### --validate

Valida a estrutura de um agente existente (SKILL.md, frontmatter, arquivos).

### --test

Roda testes automatizados em um agente existente (with_skill vs baseline).

### --analyze

Analisa falhas nos testes e sugere correcoes. Classifica cada falha em categorias (missing_resource, ambiguous_instruction, script_error, etc.) e mapeia para os arquivos afetados.

### --status

Le o `context.json` de um workspace e retorna o estado atual da criacao.

### --report

Gera o relatorio HTML a partir do workspace (context.json + test-results.json).

### --preflight

Verifica se o ambiente tem tudo necessario (Python, Claude CLI, disk space, permissoes).

---

## Request Schema

### create

```json
{
  "action": "create",
  "agent_name": "design-agent",
  "requirements": {
    "purpose": "Criar designs profissionais para websites",
    "triggers": ["design", "layout", "ui", "visual"],
    "tools": ["Write", "Read", "Bash"],
    "output_format": "HTML/CSS files",
    "edge_cases": ["mobile responsive", "dark mode"],
    "example_scenario": "Usuario pede um landing page moderna"
  },
  "options": {
    "auto_test": true,
    "max_corrections": 3,
    "output_dir": "./agents",
    "skip_phases": []
  }
}
```

### validate

```json
{
  "action": "validate",
  "agent_path": "./agents/design-agent"
}
```

### test

```json
{
  "action": "test",
  "agent_path": "./agents/design-agent",
  "workspace_path": "./agents/design-agent-workspace",
  "options": {
    "iteration": 1,
    "resume": false
  }
}
```

### analyze

```json
{
  "action": "analyze",
  "agent_path": "./agents/design-agent",
  "workspace_path": "./agents/design-agent-workspace",
  "options": {
    "iteration": 1
  }
}
```

Omit `iteration` to auto-detect the latest.

### status

```json
{
  "action": "status",
  "workspace_path": "./agents/design-agent-workspace"
}
```

Alternativa por nome:
```json
{
  "action": "status",
  "agent_name": "design-agent"
}
```

### report

```json
{
  "action": "report",
  "workspace_path": "./agents/design-agent-workspace",
  "output_path": "./report.html"
}
```

### preflight

```json
{
  "action": "preflight",
  "options": {
    "output_dir": "./agents"
  }
}
```

Ou sem body (usa defaults):
```bash
python3 agent-creator/scripts/cli_bridge.py --preflight < /dev/null
```

---

## Response Schema

### Sucesso (exit code 0)

```json
{
  "status": "success",
  "action": "<action-name>",
  "timestamp": "2026-03-17T10:30:00+00:00",
  "...": "campos especificos da action"
}
```

### Erro (exit code 1)

```json
{
  "status": "error",
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable description"
  },
  "timestamp": "2026-03-17T10:30:00+00:00"
}
```

### Parcial (exit code 2)

```json
{
  "status": "partial",
  "action": "create",
  "phase_completed": 3,
  "errors": ["Description of what failed"],
  "...": "campos da action"
}
```

### Response do --create

```json
{
  "status": "success",
  "action": "create",
  "agent_name": "design-agent",
  "agent_path": "./agents/design-agent",
  "workspace_path": "./agents/design-agent-workspace",
  "phase_completed": 6,
  "test_results": {
    "passed": 3,
    "failed": 0,
    "total": 3
  },
  "corrections_applied": 1,
  "files_created": [
    "SKILL.md",
    "scripts/generate_design.py",
    "references/design-patterns.md"
  ],
  "errors": [],
  "timestamp": "2026-03-17T10:30:00+00:00"
}
```

### Response do --analyze

```json
{
  "status": "success",
  "action": "analyze",
  "agent_path": "./agents/design-agent",
  "workspace_path": "./agents/design-agent-workspace",
  "total_failures": 2,
  "categories": {
    "ambiguous_instruction": 1,
    "script_error": 1
  },
  "corrections": [
    {
      "file": "SKILL.md",
      "failure_count": 1,
      "issues": [
        {
          "eval_id": 1,
          "expectation": "Output should follow template",
          "evidence": "Format was ambiguous, no template provided",
          "category": "ambiguous_instruction"
        }
      ],
      "suggested_actions": [
        "Instructions in SKILL.md are too vague. Add specific steps, templates, or examples."
      ]
    }
  ],
  "timestamp": "2026-03-17T10:30:00+00:00"
}
```

### Response do --preflight

```json
{
  "status": "success",
  "action": "preflight",
  "checks": [
    {"check": "python_version", "passed": true, "current": "3.11", "required": "3.8+"},
    {"check": "claude_cli", "passed": true, "path": "/usr/bin/claude", "version": "1.0.0"},
    {"check": "write_permission", "passed": true, "path": "./agents"},
    {"check": "disk_space", "passed": true, "free_mb": 5120.3, "required_mb": 100},
    {"check": "platform", "passed": true, "os": "Linux", "arch": "x86_64"}
  ],
  "summary": {"total": 5, "passed": 5, "failed": 0}
}
```

---

## Codigos de Erro

| Code | Significado |
|------|-------------|
| `MISSING_PARAM` | Parametro obrigatorio ausente no request |
| `NOT_FOUND` | Agente ou workspace nao encontrado |
| `INVALID_INPUT` | JSON invalido no stdin |
| `UNKNOWN_ACTION` | Action nao reconhecida |
| `TIMEOUT` | Execucao excedeu o timeout |
| `CLAUDE_NOT_FOUND` | CLI do Claude nao instalado |
| `REPORT_FAILED` | Falha ao gerar relatorio |
| `INTERNAL_ERROR` | Erro inesperado (ver stderr para detalhes) |

---

## Exemplos Python

### Criar agente

```python
import subprocess
import json

request = {
    "action": "create",
    "agent_name": "code-reviewer",
    "requirements": {
        "purpose": "Revisar codigo Python e sugerir melhorias",
        "triggers": ["review", "code review", "revisa esse codigo"],
        "tools": ["Read", "Grep", "Glob"],
        "output_format": "Markdown report with categorized issues"
    },
    "options": {
        "auto_test": True,
        "output_dir": "./my-agents"
    }
}

result = subprocess.run(
    ["python3", "agent-creator/scripts/cli_bridge.py", "--create"],
    input=json.dumps(request),
    capture_output=True,
    text=True,
    timeout=660
)

response = json.loads(result.stdout)

if response["status"] == "success":
    print(f"Agent created at: {response['agent_path']}")
    print(f"Tests: {response['test_results']['passed']}/{response['test_results']['total']}")
else:
    print(f"Error: {response.get('errors', [])}")
```

### Verificar se precisa criar agente

```python
def needs_agent(skill_name, skills_dir="./agents"):
    """Check if a skill/agent exists. If not, create it."""
    agent_path = Path(skills_dir) / skill_name
    if (agent_path / "SKILL.md").exists():
        return False  # Agent already exists
    return True

def auto_create_agent(purpose, triggers, skills_dir="./agents"):
    """Auto-create an agent when one doesn't exist for a task."""
    # Generate name from purpose
    agent_name = purpose.lower().replace(" ", "-")[:30]

    request = {
        "action": "create",
        "agent_name": agent_name,
        "requirements": {
            "purpose": purpose,
            "triggers": triggers,
            "tools": ["Read", "Write", "Bash"],
            "output_format": "Determined by purpose"
        },
        "options": {"output_dir": skills_dir, "auto_test": True}
    }

    result = subprocess.run(
        ["python3", "agent-creator/scripts/cli_bridge.py", "--create"],
        input=json.dumps(request),
        capture_output=True, text=True, timeout=660
    )

    return json.loads(result.stdout)
```

### Preflight check

```python
result = subprocess.run(
    ["python3", "agent-creator/scripts/cli_bridge.py", "--preflight"],
    input="{}",
    capture_output=True, text=True
)

preflight = json.loads(result.stdout)
if not preflight["passed"]:
    failed = [c for c in preflight["checks"] if not c["passed"]]
    for check in failed:
        print(f"FAIL: {check['check']}: {check['message']}")
```

---

## Exemplos Node.js

### Criar agente

```javascript
const { execSync } = require('child_process');

const request = {
  action: 'create',
  agent_name: 'api-builder',
  requirements: {
    purpose: 'Build REST APIs with Express.js',
    triggers: ['create api', 'build api', 'rest api', 'express'],
    tools: ['Write', 'Read', 'Bash'],
    output_format: 'JavaScript files with Express routes'
  },
  options: { auto_test: true, output_dir: './agents' }
};

try {
  const result = execSync(
    'python3 agent-creator/scripts/cli_bridge.py --create',
    { input: JSON.stringify(request), timeout: 660000 }
  );
  const response = JSON.parse(result.toString());
  console.log(`Agent created: ${response.agent_path}`);
} catch (err) {
  const response = JSON.parse(err.stdout?.toString() || '{}');
  console.error(`Error: ${response.error?.message}`);
}
```

### Usando com child_process.spawn (streaming)

```javascript
const { spawn } = require('child_process');

function createAgent(request) {
  return new Promise((resolve, reject) => {
    const proc = spawn('python3', [
      'agent-creator/scripts/cli_bridge.py', '--create'
    ]);

    let stdout = '';
    let stderr = '';

    proc.stdout.on('data', (data) => { stdout += data.toString(); });
    proc.stderr.on('data', (data) => {
      stderr += data.toString();
      // Log progress from stderr
      process.stderr.write(data);
    });

    proc.on('close', (code) => {
      try {
        const response = JSON.parse(stdout);
        resolve({ code, response });
      } catch (e) {
        reject(new Error(`Invalid JSON: ${stdout}`));
      }
    });

    proc.stdin.write(JSON.stringify(request));
    proc.stdin.end();
  });
}
```

### Validar agente

```javascript
const { execSync } = require('child_process');

const result = execSync(
  'python3 agent-creator/scripts/cli_bridge.py --validate',
  { input: JSON.stringify({ agent_path: './agents/my-agent' }) }
);

const { valid, message } = JSON.parse(result.toString());
console.log(valid ? 'Valid!' : `Invalid: ${message}`);
```

---

## Fluxo Tipico de Integracao CLI

```
1. CLI detecta que nao existe skill para a tarefa
   |
2. CLI chama --preflight para verificar ambiente
   |
3. CLI chama --create com requirements do usuario
   |
4. agent-creator cria o agente (fases 1-6)
   |
5. CLI chama --validate para confirmar estrutura
   |
6. CLI instala o agente em ~/.claude/commands/ ou projeto local
   |
7. Proximo request do usuario usa o agente recem-criado
```
