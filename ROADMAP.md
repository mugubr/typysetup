# Roadmap de Melhorias — TyPySetup

> Plano criado em 2026-07-04, logo após o lançamento da v2.1.0.
> Baseado em análise do código, cobertura de testes, estado das dependências e
> aprendizados do próprio ciclo de release (falha de `ensurepip` no 3.10, OIDC, etc.).

## Estado atual (v2.1.0) — forças

- ✅ Arquitetura em fases (`commands/phases/`) — coesa, testável, com delegates finos
- ✅ mypy 0 erros e **bloqueante** no CI; ruff + black limpos
- ✅ 454 testes, 2 skips ambientais, cobertura 73%
- ✅ CI em matriz 3.11–3.13; publicação via OIDC Trusted Publishing (sem tokens)
- ✅ Dependências atualizadas (pydantic 2.13, rich 15, typer 0.26, pytest 9, mypy 2.1)

---

## 1. Higiene e atualização de tecnologias (v2.2.0)

### 1.1 Modernizar os settings de VSCode dos templates ⚠️ prioridade

Os templates geram settings **removidos da extensão ms-python desde 2023**:
`python.linting.*`, `python.formatting.provider` e `editor.defaultFormatter:
ms-python.python` (inválido como formatter) não têm mais efeito. Os templates
recomendam pylint mas instalam a extensão do ruff.

**Ação**: trocar para o padrão atual em todos os 6 YAMLs:

```yaml
vscode_settings:
  "[python]":
    editor.defaultFormatter: "charliermarsh.ruff"
    editor.formatOnSave: true
    editor.codeActionsOnSave:
      source.organizeImports: "explicit"
vscode_extensions:
  - ms-python.python
  - ms-python.vscode-pylance
  - charliermarsh.ruff
```

### 1.2 Atualizar metadados e dependências dos templates

- `django.yaml` declara `python_version: "3.8+"`, mas Django 5.x exige 3.10+;
  `data-science`/`ml-ai` declaram 3.9+ — pisos irreais para as libs atuais
- Revisar pins de dependências de cada template (fastapi, django, pandas, torch...)
- Remover `ms-python.black-formatter` das extensões (redundante com ruff)

### 1.3 Consolidar black → `ruff format`

Black e ruff fazem trabalho duplicado hoje. `ruff format` é estável e
compatível com o estilo black: **uma ferramenta a menos** no dev, no CI e no
CONTRIBUTING. Ação: remover black das dev-deps, trocar `black --check` por
`ruff format --check` no CI e nos docs.

### 1.4 Remover código morto: `utils/performance.py`

Nenhum módulo importa `measure_time`/`get_global_timer` (0% de cobertura,
128 statements). Remover — ou, se a instrumentação for desejada, integrá-la às
fases do orchestrator (medindo venv/instalação) com testes.

### 1.5 Python 3.14 na matriz

O 3.14 é estável desde out/2025 e o projeto ainda não o testa/declara.
Ação: adicionar `"3.14"` na matriz do CI, classifier no pyproject e no gate de
publicação (testar 3.11 e 3.14 como extremos). Preparar para o 3.15 (out/2026).

### 1.6 PEP 735 — `[dependency-groups]`

Migrar as dev-deps de `[project.optional-dependencies].dev` para
`[dependency-groups]` (suportado nativamente pelo uv): dev-deps deixam de ser
um extra instalável do pacote publicado, que é semanticamente incorreto.
O extra `release` pode permanecer ou migrar junto.

### 1.7 Substituir `pytest-watch`

Sem manutenção há anos. Trocar por `pytest-watcher` ou simplesmente remover
(quem usa uv roda `uv run ptw` raramente).

### 1.8 Cobertura: 73% → 80% com gate

Meta de 80% com `--cov-fail-under=80` no CI. Lacunas concentradas:

| Módulo | Cobertura |
| --- | --- |
| `commands/help_cmd.py` | 11% |
| `commands/preferences_cmd.py` | 14% |
| `utils/prompts.py` | 55% |
| `commands/setup_orchestrator.py` | 68% |

Com as fases extraídas, testar `SelectionPhase`/`SummaryPhase` diretamente
ficou barato — maior retorno por teste escrito.

### 1.9 CI no Windows

Os testes já têm skips específicos de plataforma, mas o CI roda só em Ubuntu —
e a ferramenta manipula venvs e paths, onde Windows mais diverge.
Ação: `strategy.matrix.os: [ubuntu-latest, windows-latest]` (Windows pode rodar
só 3.11 e 3.14 para economizar minutos).

### 1.10 Endurecimento pendente (da revisão de segurança da 2.0.0)

- `chmod 0600` em `~/.typysetup/preferences.json` e `.typysetup/config.json`
  (contêm nome/e-mail do autor e paths do sistema)
- mypy strict gradual: ligar `disallow_untyped_defs = true` módulo a módulo
  (começar por `models/` e `utils/`, que já estão praticamente tipados)

---

## 2. Novas funcionalidades

### 2.1 Modo não-interativo (v2.3.0) ⚠️ maior alavanca de adoção

Hoje o setup é 100% wizard. Um modo por flags destrava CI, scripts, dotfiles
e **agentes de IA** como consumidores:

```bash
typysetup setup ~/api --type fastapi --manager uv --python 3.12 \
  --groups core,dev --no-extensions --yes
```

A arquitetura em fases já deixa isso barato: basta uma `NonInteractiveSelectionPhase`
que lê as flags em vez de prompts — o orchestrator não muda.

### 2.2 `typysetup doctor` (v2.3.0)

Diagnóstico do ambiente — inspirado diretamente no bug de `ensurepip` do 3.10
que travou a release 2.0.0:

- Pythons encontrados no PATH e se cada um cria venv funcional (teste real de `ensurepip`)
- Package managers disponíveis (uv/pip/poetry) e versões
- Estado de `~/.typysetup/` (permissões, JSON válido)
- Venv do projeto atual: íntegro? interpretador do VSCode aponta para ele?

### 2.3 Templates customizados do usuário (v2.4.0)

Carregar setup types também de `~/.typysetup/templates/*.yaml` (mesmo schema
dos bundled — o `ConfigLoader`/registry já suporta o formato). Times criam
templates internos sem fork. Incluir `typysetup templates validate <arquivo>`.

### 2.4 Scaffolding de arquivos iniciais (v2.4.0)

Além de pyproject/gitignore/vscode, gerar starters opcionais por template:
`main.py` (fastapi/cli), `notebooks/` (data-science), `.pre-commit-config.yaml`
com ruff/mypy. Nova responsabilidade natural da `ScaffoldPhase`.

### 2.5 `git init` + primeiro commit opcional (v2.4.0)

Já geramos `.gitignore`; oferecer `git init` + commit inicial fecha o ciclo
(pular silenciosamente se já for repositório).

### 2.6 `typysetup update` (v3.0.0)

Re-sincronizar um projeto existente com o template atual: novos settings de
VSCode (merge não-destrutivo já existe), extensões novas, pisos de Python.
Usa o `.typysetup/config.json` que todo setup já grava.

### 2.7 Venv configurável: `.venv` vs `venv` (v3.0.0, breaking)

Hoje criamos `venv/`; a convenção do ecossistema (uv, VSCode auto-detect)
convergiu para `.venv/`. Tornar configurável com default novo `.venv` na 3.0.0
(breaking para quem automatiza em cima do path atual). Preferência do usuário
em `preferences.json`.

---

## 3. Resumo por release

| Release | Tema | Itens |
| --- | --- | --- |
| **2.2.0** | Higiene + plataforma | 1.1–1.10 (templates modernos, ruff format, 3.14, PEP 735, cobertura 80%, Windows CI, chmod 0600) |
| **2.3.0** | Automação | 2.1 modo não-interativo, 2.2 doctor |
| **2.4.0** | Extensibilidade | 2.3 templates customizados, 2.4 scaffolding, 2.5 git init |
| **3.0.0** | Consolidação | 2.6 update, 2.7 `.venv` default, mypy strict total |

## Critérios de pronto (todas as releases)

- Suíte verde em todas as plataformas/versões da matriz
- Cobertura ≥ 80% (a partir da 2.2.0)
- mypy 0 erros; ruff limpo
- CHANGELOG atualizado no formato Keep a Changelog
- Fluxo de release do `RELEASING.md` (tag → TestPyPI → PyPI → GitHub Release)
