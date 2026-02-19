# Changelog

Todas as mudanças notáveis neste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere ao [Semantic Versioning](https://semver.org/lang/pt-BR/).

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
