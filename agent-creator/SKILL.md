---
name: agent-creator
description: Criar agentes completos e profissionais do zero, incluindo skill, testes e empacotamento. Use quando o usuário quiser criar um agente, bot, assistente, sistema autônomo, ou qualquer workflow baseado em Claude. Também use quando mencionarem "criar agente", "fazer um agente", "agent creator", "novo agente", "create agent", "build agent", "make an agent", ou quiserem transformar um fluxo de trabalho em agente autônomo, mesmo que não usem a palavra "agente" explicitamente.
---

# Agent Creator

Um skill que cria outros agentes completos, testados e prontos para uso. O processo é totalmente guiado: desde a captura de requisitos até a entrega final com testes passando.

## Visão Geral do Workflow

O Agent Creator segue 6 fases sequenciais. Mantenha o progresso salvo em `context.json` no workspace do agente para que o processo possa ser retomado a qualquer momento.

```
Fase 1: Captura de Requisitos  →  Entrevistar o usuário
Fase 2: Geração do Agente      →  Criar SKILL.md + estrutura
Fase 3: Criação de Testes       →  Gerar test cases realistas
Fase 4: Execução e Validação    →  Rodar testes, grading
Fase 5: Auto-Correção           →  Corrigir falhas automaticamente
Fase 6: Entrega                 →  Empacotar e entregar
```

---

## Fase 1: Captura de Requisitos

Antes de escrever qualquer código, entenda profundamente o que o usuário precisa. Se a conversa já contém contexto (ex: "transforma isso num agente"), extraia o máximo possível antes de perguntar.

### Perguntas essenciais:

1. **Propósito**: O que esse agente deve fazer? Qual problema ele resolve?
2. **Gatilho**: Quando o agente deve ser ativado? Que frases ou contextos?
3. **Ferramentas**: O agente precisa de acesso a ferramentas específicas? (Bash, Read, Write, Edit, web search, MCPs?)
4. **Formato de saída**: O que o agente produz? (código, relatório, arquivo, resposta conversacional?)
5. **Edge cases**: Quais situações incomuns o agente deve lidar?
6. **Exemplo**: Pode descrever um cenário de uso completo do início ao fim?

### Salvando contexto

Crie o workspace do agente como diretório irmão do skill que será criado:

```
<agent-name>/               ← o skill do agente
<agent-name>-workspace/     ← workspace com contexto e testes
├── context.json            ← estado persistente do processo
└── evals/
    └── evals.json          ← test cases
```

Salve as respostas em `context.json`. Consulte `references/schemas.md` para o formato completo.

```json
{
  "agent_name": "nome-do-agente",
  "status": "requirements",
  "phase": 1,
  "requirements": {
    "purpose": "Resposta do usuário...",
    "triggers": ["frase 1", "frase 2"],
    "tools": ["Bash", "Read", "Write"],
    "output_format": "Descrição do formato...",
    "edge_cases": ["caso 1", "caso 2"],
    "example_scenario": "Cenário descrito pelo usuário..."
  },
  "created_files": [],
  "test_history": [],
  "corrections": [],
  "timestamp": ""
}
```

Confirme os requisitos com o usuário antes de prosseguir: "Entendi que o agente deve [resumo]. Está correto?"

---

## Fase 2: Geração do Agente

Com os requisitos confirmados, gere a estrutura completa do agente.

### Estrutura padrão de um agente

```
<agent-name>/
├── SKILL.md                 ← Definição principal (obrigatório)
├── agents/                  ← Subagentes se necessário
│   └── <sub-agent>.md
├── scripts/                 ← Scripts auxiliares
│   └── <script>.py
├── references/              ← Documentação de referência
│   └── <ref>.md
└── assets/                  ← Templates, arquivos estáticos
    └── <asset>.*
```

### Regras de escrita do SKILL.md

Consulte `references/agent-template.md` para o template completo. Regras principais:

1. **Frontmatter YAML obrigatório**: `name` (kebab-case) e `description` (até 1024 chars)
2. **Description "pushy"**: Inclua variações de trigger para que o agente seja ativado facilmente. Não seja tímido — liste explicitamente contextos e frases que devem ativar o skill
3. **Forma imperativa**: Use "Faça X" em vez de "O agente deve fazer X"
4. **Progressive disclosure**: Mantenha SKILL.md < 500 linhas. Use `references/` para conteúdo adicional
5. **Exemplos concretos**: Inclua pelo menos 2 exemplos de input/output
6. **Sem surpresas**: O skill não deve fazer nada inesperado ou perigoso

### Gerando scripts auxiliares

Se o agente precisa de scripts:
- Use Python 3 com bibliotecas padrão quando possível
- Inclua `#!/usr/bin/env python3` e docstring
- Trate erros com mensagens claras
- Retorne exit codes adequados (0 = sucesso, 1 = erro)

### Atualize context.json

```json
{
  "status": "generated",
  "phase": 2,
  "created_files": ["SKILL.md", "scripts/main.py", "..."]
}
```

---

## Fase 3: Criação de Testes

Gere 3-5 test cases que simulem cenários reais de uso do agente.

### Formato dos test cases

Salve em `<agent-name>-workspace/evals/evals.json`:

```json
{
  "skill_name": "nome-do-agente",
  "evals": [
    {
      "id": 1,
      "prompt": "Prompt realista que um usuário diria",
      "expected_output": "Descrição do resultado esperado",
      "files": [],
      "expectations": [
        "O agente deve produzir X",
        "O output deve conter Y",
        "Nenhum erro deve ocorrer"
      ]
    }
  ]
}
```

### Boas práticas para test cases

- **Cenário principal**: O caso de uso mais comum
- **Edge case**: Uma situação incomum que o agente deve lidar
- **Input inválido**: O que acontece com entrada inesperada?
- **Cenário complexo**: Um caso que testa múltiplas capacidades
- Mostre os test cases ao usuário: "Criei estes cenários de teste. Fazem sentido?"

Atualize `context.json` com `"status": "testing", "phase": 3`.

---

## Fase 4: Execução e Validação

### Passo 0: Preflight (verificação do ambiente)

Antes de rodar testes, verifique que o ambiente está pronto:

```bash
python3 agent-creator/scripts/preflight.py
```

Isso checa: Python 3.8+, Claude CLI instalado, permissões de escrita, espaço em disco. Se algum check falhar, resolva antes de prosseguir.

### Passo 1: Validação estrutural

Execute o script de validação para verificar a estrutura:

```bash
python3 agent-creator/scripts/validate_agent.py <path-to-agent>
```

Se falhar, corrija os problemas antes de prosseguir.

### Passo 2: Rodar os testes

Para cada test case, lance subagentes em paralelo. Use `--resume` para retomar testes incompletos:

```bash
python3 agent-creator/scripts/test_agent.py <agent-path> <workspace-path> --iteration N --resume
```

O script cria arquivos temporários em `.claude/commands/` para que Claude descubra o skill, remove a variável `CLAUDECODE` do env para nesting seguro, e pula evals que já possuem resultado (resume).

Alternativamente, lance subagentes manualmente:

**Com o skill (teste principal):**
```
Execute esta tarefa:
- Skill path: <path-to-agent>
- Task: <eval prompt>
- Input files: <eval files ou "nenhum">
- Salve outputs em: <workspace>/iteration-<N>/eval-<ID>/with_skill/outputs/
```

**Sem o skill (baseline):**
```
Execute esta tarefa:
- Sem skill
- Task: <eval prompt>
- Salve outputs em: <workspace>/iteration-<N>/eval-<ID>/without_skill/outputs/
```

### Passo 3: Grading

Use o subagente `agents/agent-tester.md` para avaliar cada resultado:

```
Avalie estes resultados:
- Expectations: <lista de expectations>
- Transcript path: <path do transcript>
- Outputs dir: <path dos outputs>
Retorne JSON com pass/fail para cada expectation.
```

### Passo 4: Coletar resultados

Salve resultados em `<workspace>/iteration-<N>/test-results.json`:

```json
{
  "iteration": 1,
  "timestamp": "2026-03-17T...",
  "results": [
    {
      "eval_id": 1,
      "passed": true,
      "expectations": [
        {"text": "O agente deve...", "verdict": "PASS", "evidence": "..."}
      ]
    }
  ],
  "summary": {"total": 5, "passed": 4, "failed": 1}
}
```

---

## Fase 5: Auto-Correção

Se algum teste falhou, entre no loop de auto-correção. Máximo de 3 iterações.

### Passo 1: Análise automatizada

Execute o script de análise para identificar o que quebrou e onde:

```bash
python3 agent-creator/scripts/auto_correct.py <agent-path> <workspace-path>
```

O script classifica cada falha (ambiguous_instruction, script_error, output_format, edge_case, trigger_failure, etc.), mapeia para o arquivo afetado, e sugere ações corretivas.

Para output JSON (útil para integração programática):
```bash
python3 agent-creator/scripts/auto_correct.py <agent-path> <workspace-path> --json
```

### Passo 2: Aplicar correções

Com base na análise, corrija os arquivos:
   - Instrução ambígua no SKILL.md? → Reescreva a seção
   - Bug no script? → Corrija o código
   - Expectation impossível? → Ajuste o test case
   - Falta de tratamento de edge case? → Adicione instrução

Edite os arquivos necessários.

### Passo 3: Documentar correções

Adicione ao `context.json`:
```json
{
  "corrections": [
    {
      "iteration": 2,
      "file": "SKILL.md",
      "issue": "Instrução de formato de saída era ambígua",
      "fix": "Adicionado template explícito na seção Output"
    }
  ]
}
```

### Passo 4: Re-executar testes

Volte à Fase 4 com a nova iteração.

### Passo 5: Avaliar progresso

Se os mesmos testes continuam falhando após 3 iterações, peça ajuda ao usuário: "Não consegui corrigir automaticamente o problema X. Pode me ajudar?"

---

## Fase 6: Entrega

Quando todos os testes passarem (ou o usuário estiver satisfeito):

### Passo 1: Validação final

```bash
python3 skill-creator/scripts/quick_validate.py <path-to-agent>
```

### Passo 2: Gerar relatório

Gere o relatório HTML automaticamente e apresente um resumo ao usuário:

```bash
python3 agent-creator/scripts/generate_report.py <workspace-path> --output report.html
```

Ou apresente diretamente no chat:

```
## Agente Criado: <nome>

**Descrição**: <o que faz>
**Arquivos**: <lista de arquivos criados>
**Testes**: <X/Y passaram>
**Correções aplicadas**: <N correções em M iterações>

### Como usar
1. Copie a pasta `<agent-name>/` para `~/.claude/commands/` ou seu projeto
2. O agente será ativado quando você disser: <triggers>
3. Exemplo: "<frase de exemplo>"
```

### Passo 3: Empacotar (opcional)

Se o usuário quiser distribuir o agente:

```bash
python3 skill-creator/scripts/package_skill.py <path-to-agent>
```

### Passo 4: Atualizar context.json final

```json
{
  "status": "delivered",
  "phase": 6,
  "final_test_results": {"passed": 5, "failed": 0},
  "delivery_timestamp": "2026-03-17T..."
}
```

---

## Retomando o processo

Se o usuário voltar depois de uma interrupção, leia o `context.json` para entender em que fase parou e retome de lá. O campo `phase` indica a fase atual, e `status` indica o estado dentro da fase.

## Comunicação com o usuário

- Adapte a linguagem ao nível técnico do usuário
- Se não sabe o nível, comece acessível e ajuste conforme os sinais
- Explique termos técnicos brevemente quando em dúvida
- Mostre progresso: "Fase 2 de 6: Gerando o agente..."
- Peça confirmação em pontos-chave: após requisitos, após test cases, antes da entrega

---

## Invocação via CLI Externo

O agent-creator pode ser chamado programaticamente por CLIs externos (Python, Node.js) através do `scripts/cli_bridge.py`. Isso permite que um CLI detecte a falta de um agente e crie automaticamente.

### Cenário típico

```
1. Usuário pede: "quero um site com design top"
2. CLI detecta que não existe skill/agente de design
3. CLI chama agent-creator via cli_bridge.py
4. Agent-creator cria o agente de design (fases 1-6)
5. CLI instala o agente recém-criado
6. Próximo request usa o agente de design
```

### Como chamar

```bash
echo '{"action":"create","agent_name":"design-agent","requirements":{"purpose":"Design profissional","triggers":["design","layout"]}}' | python3 agent-creator/scripts/cli_bridge.py --create
```

### Actions disponíveis

| Action | Flag | Descrição |
|--------|------|-----------|
| create | `--create` | Criação completa (fases 1-6) |
| validate | `--validate` | Validar estrutura de um agente |
| test | `--test` | Rodar testes em um agente |
| analyze | `--analyze` | Analisar falhas e sugerir correções |
| status | `--status` | Ler progresso de uma criação |
| report | `--report` | Gerar relatório HTML |
| preflight | `--preflight` | Verificar ambiente |

### Protocolo

- **Input**: JSON via stdin
- **Output**: JSON via stdout
- **Logs**: stderr (human-readable)
- **Exit codes**: 0=sucesso, 1=erro, 2=parcial

Consulte `references/cli-protocol.md` para documentação completa com exemplos Python e Node.js.

### Integração Python

```python
import subprocess, json

result = subprocess.run(
    ["python3", "agent-creator/scripts/cli_bridge.py", "--create"],
    input=json.dumps({
        "agent_name": "design-agent",
        "requirements": {"purpose": "Criar designs profissionais"},
        "options": {"output_dir": "./agents", "auto_test": True}
    }),
    capture_output=True, text=True
)
response = json.loads(result.stdout)
```

### Integração Node.js

```javascript
const { execSync } = require('child_process');
const result = execSync(
    'python3 agent-creator/scripts/cli_bridge.py --create',
    { input: JSON.stringify({
        agent_name: 'design-agent',
        requirements: { purpose: 'Criar designs profissionais' },
        options: { output_dir: './agents', auto_test: true }
    })}
);
const response = JSON.parse(result.toString());
```

## Scripts disponíveis

| Script | Função |
|--------|--------|
| `scripts/cli_bridge.py` | Ponte CLI - entry point programático (7 actions) |
| `scripts/validate_agent.py` | Validação estrutural do agente |
| `scripts/test_agent.py` | Execução de testes com resume |
| `scripts/auto_correct.py` | Análise de falhas e plano de correção |
| `scripts/preflight.py` | Verificação do ambiente |
| `scripts/generate_report.py` | Geração de relatório HTML |
