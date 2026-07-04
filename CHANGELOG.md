# Changelog

Todas as mudanças notáveis neste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere ao [Semantic Versioning](https://semver.org/lang/pt-BR/).

## [2.1.0] - 2026-07-03

### ⚠️ Breaking Changes
- **Suporte mínimo de Python elevado para 3.11.** O gate de testes da 2.0.0 revelou que builds standalone do Python 3.10 (usados por `uv python install` e pelos runners de CI) falham ao criar venvs com `ensurepip`; com o fim de vida do 3.10 se aproximando, o piso foi elevado direto para 3.11. Como a 2.0.0 nunca chegou ao PyPI, esta é a primeira release da linha 2.x (1.1.0 → 2.1.0) e inclui todas as mudanças da seção 2.0.0 abaixo.

### Changed
- **`SetupOrchestrator` refatorado em classes de fase** (`commands/phases/`): `SelectionPhase` (prompts interativos), `ScaffoldPhase` (.gitignore, VSCode, pyproject.toml), `EnvironmentPhase` (venv + dependências) e `SummaryPhase` (relatório final). O orchestrator mantém a API pública e delega às fases — cada fase é testável isoladamente com dependências explícitas.
- Modernizações habilitadas pelo Python 3.11: `datetime.UTC`, `tomllib` da stdlib nos testes (dependência condicional `tomli` removida) e `enum.StrEnum` em `ConstraintType`.
- Matriz de CI reduzida para Python 3.11–3.13; gate de publicação testa 3.11 e 3.13.
- Workflows endurecidos: bloco `permissions: contents: read` de menor privilégio no nível raiz e actions de terceiros (`pypa/gh-action-pypi-publish`, `softprops/action-gh-release`, `astral-sh/setup-uv`) pinadas por SHA imutável.

### Fixed
- **Débito de tipos quitado: mypy passa com 0 erros e agora é bloqueante no CI** (na 2.0.0 rodava como informativo com 47 erros conhecidos).
- **Os 12 testes E2E do orchestrator marcados como `skip` na 2.0.0 foram reescritos** contra as novas classes de fase — sem mocks acoplados a estrutura interna e sem paths hardcoded; a suíte roda sem skips estruturais.

### Migration Guide
- **Python**: garanta Python 3.11 ou superior (`python --version`).
- **Vindo da 1.x**: aplique também o guia de migração da seção 2.0.0 abaixo — todas aquelas mudanças fazem parte desta release.
- **Preferências e histórico**: nenhum passo necessário — os formatos de `~/.typysetup/preferences.json` e `.typysetup/config.json` permanecem compatíveis.

## [2.0.0] - 2026-07-03 (não publicada)

> Esta versão foi preparada mas **nunca publicada no PyPI**: o gate de testes de release falhou no Python 3.10 (falha de `ensurepip` em builds standalone). Todas as suas mudanças foram incorporadas e lançadas na 2.1.0.

### ⚠️ Breaking Changes
- **Suporte mínimo de Python elevado para 3.10** (Python 3.8 e 3.9 atingiram fim de vida). Ambientes rodando typysetup em 3.8/3.9 precisam atualizar o interpretador.
- `build` e `twine` deixaram de ser dependências de runtime; foram movidos para o extra opcional `release`. Instalações do CLI ficam significativamente mais enxutas.

### Added
- Configuração automática de `python.defaultInterpreterPath` no `settings.json` do VSCode, apontando para o venv do projeto (`${workspaceFolder}/venv/bin/python`) — o editor seleciona o interpretador correto sem ação manual.
- Extra opcional `release` em `pyproject.toml` para ferramentas de build/publicação (`pip install "typysetup[release]"`).
- Workflow de CI (`.github/workflows/ci.yml`) executando ruff, black, mypy e pytest em matriz Python 3.10–3.13 a cada push/PR.
- `RELEASING.md` documentando o processo de release e a configuração de Trusted Publishing (OIDC) no PyPI.
- Helper `utils/datetime_utils.utc_now()` centralizando a geração de timestamps UTC.

### Changed
- Todas as dependências atualizadas para as versões mais recentes (typer, pydantic, rich, pyyaml, questionary, tomli-w; pytest, pytest-cov, black, ruff, mypy) e `uv.lock` regenerado.
- Anotações de tipo modernizadas para a sintaxe do Python 3.10+ (`list[str]`, `dict[str, Any]`, `X | None`).
- Workflow de publicação migrado para **OIDC Trusted Publishing** (`pypa/gh-action-pypi-publish`), eliminando tokens de longa duração, com gate de testes antes de publicar e criação automática de GitHub Release restaurada.
- Extração de nomes de pacotes agora usa `packaging.requirements.Requirement`, mais robusta para extras, markers de ambiente e URLs.

### Fixed
- Corrigido `datetime.utcnow()` deprecado em todos os modelos e gerenciadores; corrigido também `from datetime import UTC` (disponível só no 3.11+) que quebrava o suporte anunciado a Python 3.10.
- Corrigida anotação de tipo inválida `Dict[str, any]` → `Dict[str, Any]` em `config_loader`.
- Relatório de cobertura de testes passou a reportar valores reais (~72%) em vez de 0% (configuração de `coverage`/`pytest-cov`).
- Falhas silenciosas (`except Exception: pass`) ao gravar histórico do setup agora registram warning; limpeza de arquivo temporário de preferências e truncamento de histórico também passam a logar.
- Eliminados avisos de deprecação: `min_items` → `min_length` (Pydantic v2) e remoção de `is_flag` não suportado pelo Typer.

### Migration Guide
- **Python**: garanta Python 3.10 ou superior (`python --version`).
- **Build/publicação local**: instale o extra de release com `pip install "typysetup[release]"` (ou `uv sync --extra release`) caso use `build`/`twine` localmente.
- **Preferências e histórico**: nenhum passo necessário — o formato de `~/.typysetup/preferences.json` permanece compatível.

### Known Issues
- 12 testes E2E do orchestrator estão temporariamente marcados como `skip`: dependem de mocks frágeis acoplados à estrutura interna do `SetupOrchestrator` e serão reescritos junto da refatoração em classes de fase planejada para a 2.1.0. A suíte segue com 442 testes passando.
- A verificação de tipos (mypy) roda como informativa no CI: há débito de tipos pré-existente (principalmente no `SetupOrchestrator`) a ser resolvido na 2.1.0.

## [1.1.0] - 2026-02-18

### Changed
- Refatoração dos comandos CLI para classes OOP, melhorando coesão e testabilidade (`ConfigCommand`, `HelpCommand`, `HistoryCommand`, `ListCommand`, `PreferencesCommand`, `SetupOrchestrator`)

### Fixed
- Sincronização da versão exibida por `typysetup --version` com `__version__` do pacote

### Added
- Documentação hierárquica `AGENTS.md` em três níveis (raiz, `core/`, `models/`) para desenvolvimento assistido por IA

## [1.0.0] - 2026-02-02

### Added
- 🎉 Lançamento inicial do TyPySetup no PyPI
- 6 templates de projeto configurados:
  - **FastAPI** - Web API moderna e async
  - **Django** - Framework web full-stack
  - **Data Science** - Jupyter e análise de dados
  - **CLI Tool** - Aplicações de linha de comando
  - **Async/Real-time** - Aplicações assíncronas e tempo real
  - **ML/AI** - Machine Learning e Inteligência Artificial
- Wizard de setup interativo com questionary
- Suporte para 3 gerenciadores de pacotes: uv, pip, poetry
- Geração automática de configuração VSCode
- Sistema de gerenciamento de preferências do usuário
- Sistema de histórico de setups realizados
- Backup automático de arquivos antes de modificações
- Rollback em caso de falhas durante setup
- 450+ testes automatizados com 92% de aprovação
- Documentação completa:
  - README com guia de uso
  - CONTRIBUTING com guia de contribuição
  - ARCHITECTURE com design do sistema
  - TROUBLESHOOTING com resolução de problemas

### Technical Details
- **Python**: 3.8+ suportado
- **CLI Framework**: Typer
- **Data Validation**: Pydantic 2.0
- **Terminal UI**: Rich
- **Build System**: setuptools + PEP 621
- **Testing**: pytest com cobertura

### Fixed
- Corrigido formato de licença no pyproject.toml
- Corrigido datetime.utcnow() deprecated para datetime.now(UTC)
- Aumentado timeout do uv para 10 minutos para pacotes grandes

### Known Issues
- Timeout de 5 minutos no uv pode ser insuficiente para pacotes ML/AI em conexões lentas (corrigido em 1.0.0)
- Alguns testes de integração de dependências precisam ser refinados
- Cobertura de testes reportada como 0% (problema de configuração pytest-cov)

### Breaking Changes
Nenhuma (lançamento inicial)

### Migration Guide
Nenhuma (lançamento inicial)
