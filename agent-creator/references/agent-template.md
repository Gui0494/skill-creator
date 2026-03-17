# Template de Agente

Use este template como base para gerar novos agentes. Adapte conforme os requisitos específicos.

## Estrutura de Diretórios

```
<agent-name>/
├── SKILL.md                 ← Obrigatório
├── agents/                  ← Subagentes (opcional)
├── scripts/                 ← Scripts auxiliares (opcional)
├── references/              ← Docs de referência (opcional)
└── assets/                  ← Templates e arquivos estáticos (opcional)
```

## Template do SKILL.md

```markdown
---
name: <agent-name>
description: <Descrição clara do que o agente faz e quando deve ser ativado. Seja "pushy" - liste explicitamente contextos e frases de trigger. Máximo 1024 caracteres.>
---

# <Agent Name>

<Descrição curta do propósito do agente em 1-2 frases.>

## Quando usar

<Liste os cenários em que este agente é útil.>

## Workflow

### Passo 1: <Nome do passo>

<Instruções em forma imperativa. Ex: "Leia o arquivo X", não "O agente deve ler o arquivo X".>

### Passo 2: <Nome do passo>

<Instruções claras e sequenciais.>

## Formato de Saída

<Descreva exatamente o que o agente produz.>

**Exemplo:**
```
Input: <exemplo de input>
Output: <exemplo de output>
```

## Edge Cases

- <Caso especial 1>: <como lidar>
- <Caso especial 2>: <como lidar>

## Erros Comuns

- Se <situação>: <ação corretiva>
```

## Checklist de Qualidade

Antes de entregar um agente, verifique:

- [ ] `name` em kebab-case (só minúsculas, números e hífens)
- [ ] `name` com máximo 64 caracteres
- [ ] `description` com máximo 1024 caracteres
- [ ] `description` sem angle brackets (< ou >)
- [ ] SKILL.md com menos de 500 linhas
- [ ] Instruções em forma imperativa
- [ ] Pelo menos 2 exemplos de input/output
- [ ] Edge cases documentados
- [ ] Scripts com `#!/usr/bin/env python3` e docstring
- [ ] Scripts retornam exit codes adequados
- [ ] Referências apontam para arquivos existentes
- [ ] Nenhum arquivo sensível (.env, credentials, secrets)
- [ ] Progressive disclosure: detalhes pesados em references/

## Padrões de Escrita

### Description "Pushy"

Ruim:
> "Formata código Python"

Bom:
> "Formata e organiza código Python seguindo PEP 8. Use quando o usuário mencionar formatação, linting, estilo de código, PEP 8, black, autopep8, ou quiser limpar/organizar código Python, mesmo que não peça formatação explicitamente."

### Forma Imperativa

Ruim:
> "O agente deve analisar o arquivo e gerar um relatório"

Bom:
> "Analise o arquivo e gere um relatório"

### Exemplos Concretos

Sempre inclua exemplos reais. Não use placeholders genéricos.

```markdown
**Exemplo 1:**
Input: "Refatora esta função para usar async/await"
Output: Código refatorado com async/await, mantendo a mesma funcionalidade

**Exemplo 2:**
Input: "Este código está lento, otimiza"
Output: Análise de performance + código otimizado com comentários explicando as mudanças
```

## Tipos Comuns de Agentes

### Agente de Transformação
- Recebe input, aplica transformação, produz output
- Foco em: formato de entrada, regras de transformação, formato de saída
- Exemplo: conversor de formatos, refatorador de código

### Agente de Análise
- Recebe dados, analisa, produz relatório/insights
- Foco em: métricas, critérios de avaliação, formato do relatório
- Exemplo: code reviewer, analisador de logs

### Agente de Workflow
- Executa uma sequência de passos para completar uma tarefa
- Foco em: ordem dos passos, decisões condicionais, checkpoints
- Exemplo: deploy agent, migration agent

### Agente de Criação
- Gera artefatos novos a partir de especificações
- Foco em: templates, regras de geração, validação do output
- Exemplo: gerador de componentes, scaffolder
