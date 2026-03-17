# Schemas JSON - Agent Creator

Schemas para os arquivos de dados usados pelo agent-creator.

## Índice

1. [context.json](#contextjson) - Estado persistente do processo de criação
2. [evals.json](#evalsjson) - Test cases do agente criado
3. [test-results.json](#test-resultsjson) - Resultados dos testes
4. [correction-log.json](#correction-logjson) - Histórico de auto-correções

---

## context.json

Estado persistente do processo de criação. Criado na Fase 1 e atualizado em cada fase.

```json
{
  "agent_name": {
    "type": "string",
    "description": "Nome do agente em kebab-case",
    "required": true,
    "example": "code-reviewer"
  },
  "status": {
    "type": "string",
    "enum": ["requirements", "generated", "testing", "correcting", "delivered"],
    "description": "Estado atual do processo",
    "required": true
  },
  "phase": {
    "type": "integer",
    "minimum": 1,
    "maximum": 6,
    "description": "Fase atual do workflow",
    "required": true
  },
  "requirements": {
    "type": "object",
    "description": "Requisitos capturados na Fase 1",
    "properties": {
      "purpose": {
        "type": "string",
        "description": "O que o agente faz"
      },
      "triggers": {
        "type": "array",
        "items": "string",
        "description": "Frases/contextos que ativam o agente"
      },
      "tools": {
        "type": "array",
        "items": "string",
        "description": "Ferramentas necessárias (Bash, Read, Write, etc.)"
      },
      "output_format": {
        "type": "string",
        "description": "Formato esperado de saída"
      },
      "edge_cases": {
        "type": "array",
        "items": "string",
        "description": "Casos especiais a tratar"
      },
      "example_scenario": {
        "type": "string",
        "description": "Cenário de uso completo descrito pelo usuário"
      }
    }
  },
  "created_files": {
    "type": "array",
    "items": "string",
    "description": "Lista de arquivos criados para o agente"
  },
  "test_history": {
    "type": "array",
    "items": {
      "iteration": "integer",
      "passed": "integer",
      "failed": "integer",
      "total": "integer",
      "timestamp": "string (ISO 8601)"
    },
    "description": "Histórico de execuções de teste"
  },
  "corrections": {
    "type": "array",
    "items": {
      "iteration": "integer",
      "file": "string",
      "issue": "string",
      "fix": "string",
      "timestamp": "string (ISO 8601)"
    },
    "description": "Correções aplicadas durante auto-correção"
  },
  "timestamp": {
    "type": "string",
    "format": "ISO 8601",
    "description": "Última atualização"
  }
}
```

### Exemplo completo

```json
{
  "agent_name": "code-reviewer",
  "status": "delivered",
  "phase": 6,
  "requirements": {
    "purpose": "Revisar código Python e sugerir melhorias",
    "triggers": ["review this code", "revisa esse código", "code review"],
    "tools": ["Read", "Grep", "Glob"],
    "output_format": "Relatório markdown com issues categorizadas",
    "edge_cases": ["Arquivo vazio", "Código com syntax errors"],
    "example_scenario": "Usuário pede review de um arquivo main.py de 200 linhas"
  },
  "created_files": [
    "code-reviewer/SKILL.md",
    "code-reviewer/references/review-checklist.md"
  ],
  "test_history": [
    {"iteration": 1, "passed": 2, "failed": 1, "total": 3, "timestamp": "2026-03-17T10:00:00Z"},
    {"iteration": 2, "passed": 3, "failed": 0, "total": 3, "timestamp": "2026-03-17T10:30:00Z"}
  ],
  "corrections": [
    {
      "iteration": 2,
      "file": "code-reviewer/SKILL.md",
      "issue": "Não detectava code smells em funções longas",
      "fix": "Adicionada seção sobre complexidade ciclomática e tamanho de funções",
      "timestamp": "2026-03-17T10:15:00Z"
    }
  ],
  "timestamp": "2026-03-17T10:30:00Z"
}
```

---

## evals.json

Test cases para validar o agente criado. Segue o formato padrão do skill-creator.

```json
{
  "skill_name": {
    "type": "string",
    "description": "Nome do agente sendo testado",
    "required": true
  },
  "evals": {
    "type": "array",
    "required": true,
    "items": {
      "id": {
        "type": "integer",
        "description": "Identificador único do teste"
      },
      "prompt": {
        "type": "string",
        "description": "Prompt realista que um usuário diria"
      },
      "expected_output": {
        "type": "string",
        "description": "Descrição do resultado esperado"
      },
      "files": {
        "type": "array",
        "items": "string",
        "description": "Arquivos de input necessários (paths relativos)"
      },
      "expectations": {
        "type": "array",
        "items": "string",
        "description": "Assertions verificáveis sobre o output"
      }
    }
  }
}
```

---

## test-results.json

Resultados de uma iteração de testes.

```json
{
  "iteration": {
    "type": "integer",
    "description": "Número da iteração"
  },
  "timestamp": {
    "type": "string",
    "format": "ISO 8601"
  },
  "results": {
    "type": "array",
    "items": {
      "eval_id": "integer",
      "eval_name": "string",
      "passed": "boolean",
      "expectations": {
        "type": "array",
        "items": {
          "text": "string",
          "verdict": "PASS | FAIL",
          "evidence": "string"
        }
      },
      "execution_time_ms": "integer",
      "error": "string | null"
    }
  },
  "summary": {
    "total": "integer",
    "passed": "integer",
    "failed": "integer",
    "pass_rate": "number (0-1)"
  }
}
```

---

## correction-log.json

Registro detalhado de auto-correções (opcional, para auditing).

```json
{
  "agent_name": "string",
  "corrections": [
    {
      "iteration": "integer",
      "timestamp": "string (ISO 8601)",
      "failed_tests": ["integer (eval IDs)"],
      "analysis": "string (análise da causa raiz)",
      "changes": [
        {
          "file": "string (path relativo)",
          "type": "edit | create | delete",
          "description": "string (o que foi mudado)",
          "diff_summary": "string (resumo do diff)"
        }
      ],
      "result": "fixed | partial | unfixed"
    }
  ]
}
```
