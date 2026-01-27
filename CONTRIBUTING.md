# Contributing to TyPySetup

Obrigado pelo interesse em contribuir com TyPySetup! Este documento fornece orientações para contribuir com o projeto.

## Índice

- [Código de Conduta](#código-de-conduta)
- [Como Contribuir](#como-contribuir)
- [Configuração do Ambiente](#configuração-do-ambiente)
- [Padrões de Código](#padrões-de-código)
- [Processo de Desenvolvimento](#processo-de-desenvolvimento)
- [Testes](#testes)
- [Documentação](#documentação)
- [Pull Requests](#pull-requests)

---

## Código de Conduta

Este projeto adere a um código de conduta. Ao participar, espera-se que você siga este código:

- **Seja respeitoso**: Trate todos com respeito e consideração
- **Seja colaborativo**: Trabalhe junto com a comunidade
- **Seja construtivo**: Forneça feedback construtivo
- **Seja paciente**: Lembre-se que todos estão aprendendo

---

## Como Contribuir

Existem várias formas de contribuir:

### 🐛 Reportar Bugs

1. Verifique se o bug já foi reportado nas [Issues](https://github.com/user/typysetup/issues)
2. Crie uma nova issue com:
   - Descrição clara do problema
   - Passos para reproduzir
   - Comportamento esperado vs atual
   - Versões (Python, TyPySetup, OS)
   - Logs relevantes (com `--verbose`)

**Template**:
```markdown
**Descrição do Bug**
Descrição clara e concisa do problema.

**Como Reproduzir**
1. Execute `typysetup setup /tmp/test`
2. Selecione 'FastAPI'
3. Erro ocorre...

**Comportamento Esperado**
O que deveria acontecer.

**Ambiente**
- OS: Ubuntu 22.04
- Python: 3.11.0
- TyPySetup: 0.1.0
- Package Manager: uv 0.1.0

**Logs**
```bash
typysetup setup /tmp/test --verbose
```
```

### ✨ Sugerir Melhorias

1. Abra uma issue descrevendo a melhoria
2. Explique por que seria útil
3. Forneça exemplos de uso
4. Aguarde feedback da comunidade

### 📝 Melhorar Documentação

- Corrigir typos ou erros
- Adicionar exemplos
- Clarificar instruções
- Traduzir documentação

### 🔧 Contribuir com Código

Veja [Processo de Desenvolvimento](#processo-de-desenvolvimento) abaixo.

---

## Configuração do Ambiente

### Pré-requisitos

- Python 3.8 ou superior
- Git
- (Opcional) uv para instalação rápida

### Instalação

```bash
# 1. Fork e clone o repositório
git clone https://github.com/SEU-USUARIO/typysetup.git
cd typysetup

# 2. Criar virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Instalar em modo desenvolvimento
pip install -e ".[dev]"

# Ou com uv (mais rápido)
uv pip install -e ".[dev]"

# 4. Verificar instalação
typysetup --version
pytest --version
```

### Estrutura do Projeto

```
typysetup/
├── src/typysetup/           # Código fonte
│   ├── main.py            # Entry point
│   ├── models/            # Pydantic models
│   ├── commands/          # CLI commands
│   ├── core/              # Business logic
│   ├── utils/             # Utilities
│   └── configs/           # Setup type YAML files
├── tests/                 # Testes
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   └── conftest.py        # Pytest fixtures
├── docs/                  # Documentação
└── pyproject.toml         # Project metadata
```

---

## Padrões de Código

### Estilo de Código

Seguimos PEP 8 com algumas extensões:

```python
# Imports organizados
import os
import sys
from pathlib import Path
from typing import Optional, List

import typer
from pydantic import BaseModel
from rich.console import Console

from typysetup.core import ConfigLoader
from typysetup.models import SetupType

# Constantes em UPPER_CASE
DEFAULT_PYTHON_VERSION = "3.11"
MAX_RETRY_ATTEMPTS = 3

# Classes em PascalCase
class VirtualEnvironmentManager:
    """Gerencia ambientes virtuais Python."""

    def __init__(self, project_path: Path):
        self.project_path = project_path

    def create_venv(self, python_version: str = None) -> Path:
        """
        Cria um virtual environment.

        Args:
            python_version: Versão do Python (opcional)

        Returns:
            Path para o venv criado

        Raises:
            VenvCreationError: Se falhar ao criar venv
        """
        # Implementation
        pass

# Funções em snake_case
def get_python_executable(venv_path: Path) -> Path:
    """Retorna o caminho para o executável Python no venv."""
    if sys.platform == 'win32':
        return venv_path / 'Scripts' / 'python.exe'
    return venv_path / 'bin' / 'python'
```

### Type Hints

Use type hints em todas as funções:

```python
from typing import Optional, List, Dict, Any

def install_dependencies(
    venv_path: Path,
    dependencies: List[str],
    manager: str = 'uv'
) -> Dict[str, Any]:
    """Instala dependências no venv."""
    result: Dict[str, Any] = {}
    # Implementation
    return result
```

### Docstrings

Use formato Google/Sphinx:

```python
def merge_vscode_settings(
    existing: Dict[str, Any],
    new: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Merge VSCode settings with precedence to new values.

    Args:
        existing: Current settings from .vscode/settings.json
        new: New settings from setup type configuration

    Returns:
        Merged settings dictionary

    Raises:
        ValueError: If settings are invalid

    Example:
        >>> existing = {"python.linting.enabled": False}
        >>> new = {"python.linting.enabled": True}
        >>> merge_vscode_settings(existing, new)
        {'python.linting.enabled': True}
    """
    # Implementation
```

### Formatação

Usamos as seguintes ferramentas:

```bash
# Formatar código
black src/ tests/

# Ordenar imports
isort src/ tests/

# Lint
ruff check src/ tests/

# Type checking
mypy src/typysetup
```

**Configuração no pyproject.toml**:
```toml
[tool.black]
line-length = 100
target-version = ['py38']

[tool.isort]
profile = "black"
line_length = 100

[tool.ruff]
line-length = 100
select = ["E", "F", "W", "I"]

[tool.mypy]
python_version = "3.8"
strict = true
```

---

## Processo de Desenvolvimento

### 1. Criar uma Branch

```bash
# Atualizar main
git checkout main
git pull origin main

# Criar feature branch
git checkout -b feature/nome-da-feature

# Ou bugfix branch
git checkout -b fix/nome-do-bug
```

### 2. Desenvolver

```bash
# Fazer mudanças
# Testar localmente
pytest

# Verificar formatação
black src/ tests/
ruff check src/ tests/
mypy src/typysetup

# Commitar frequentemente
git add .
git commit -m "feat: adiciona nova funcionalidade X"
```

### 3. Conventional Commits

Usamos [Conventional Commits](https://www.conventionalcommits.org/):

- `feat`: Nova funcionalidade
- `fix`: Correção de bug
- `docs`: Mudanças na documentação
- `style`: Formatação, não afeta código
- `refactor`: Refatoração de código
- `test`: Adiciona ou modifica testes
- `chore`: Manutenção, build, CI

**Exemplos**:
```bash
git commit -m "feat: adiciona suporte para Python 3.12"
git commit -m "fix: corrige erro ao criar venv no Windows"
git commit -m "docs: atualiza README com novo exemplo"
git commit -m "test: adiciona testes para VSCodeConfigGenerator"
```

### 4. Testar

```bash
# Testes unitários
pytest tests/unit/

# Testes de integração
pytest tests/integration/

# Todos os testes com cobertura
pytest --cov=src/typysetup --cov-report=html

# Abrir relatório de cobertura
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

### 5. Push e Pull Request

```bash
# Push para sua fork
git push origin feature/nome-da-feature

# Criar Pull Request no GitHub
# Preencher template de PR
```

---

## Testes

### Estrutura de Testes

```
tests/
├── unit/                          # Testes unitários (isolados)
│   ├── test_config_loader.py      # Testa ConfigLoader
│   ├── test_venv_manager.py       # Testa VenvManager
│   └── ...
├── integration/                   # Testes de integração
│   ├── test_setup_flow.py         # Teste end-to-end
│   └── ...
└── conftest.py                    # Fixtures compartilhadas
```

### Escrevendo Testes

**Unit Test Exemplo**:
```python
import pytest
from pathlib import Path
from typysetup.core import ConfigLoader
from typysetup.models import SetupType

@pytest.fixture
def config_loader(tmp_path):
    """ConfigLoader com diretório temporário."""
    # Copiar YAML de teste para tmp_path
    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    # ... setup
    return ConfigLoader(config_dir)

def test_load_setup_type_valid(config_loader):
    """Deve carregar setup type válido."""
    setup_type = config_loader.load_setup_type('fastapi')

    assert setup_type.name == 'FastAPI'
    assert setup_type.slug == 'fastapi'
    assert 'fastapi' in setup_type.dependencies['core']

def test_load_setup_type_invalid_raises_error(config_loader):
    """Deve lançar erro para setup type inválido."""
    with pytest.raises(FileNotFoundError):
        config_loader.load_setup_type('invalid-type')
```

**Integration Test Exemplo**:
```python
from typer.testing import CliRunner
from typysetup.main import app

def test_setup_flow_end_to_end(tmp_path, monkeypatch):
    """Teste completo do fluxo de setup."""
    # Mock subprocess para evitar instalação real
    def mock_run(cmd, *args, **kwargs):
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr('subprocess.run', mock_run)

    # Executar comando
    runner = CliRunner()
    result = runner.invoke(app, ['setup', str(tmp_path)])

    # Verificar resultado
    assert result.exit_code == 0
    assert 'Setup complete' in result.stdout
    assert (tmp_path / 'venv').exists()
```

### Executando Testes

```bash
# Todos os testes
pytest

# Testes específicos
pytest tests/unit/test_config_loader.py
pytest tests/unit/test_config_loader.py::test_load_setup_type_valid

# Com verbose
pytest -v

# Com cobertura
pytest --cov=src/typysetup --cov-report=term-missing

# Watch mode (reexecuta ao salvar)
pytest-watch
```

### Cobertura de Testes

- **Meta**: 80%+ de cobertura
- **Prioridade**: Core logic (core/*)
- **Aceitável**: UI code pode ter cobertura menor

---

## Documentação

### Tipos de Documentação

1. **Docstrings**: Todas as classes e funções públicas
2. **README**: Overview e quick start
3. **ARCHITECTURE**: Design e padrões
4. **CONTRIBUTING**: Este arquivo
5. **TROUBLESHOOTING**: Problemas comuns

### Adicionando Novo Setup Type

```yaml
# 1. Criar arquivo YAML em src/typysetup/configs/
# exemplo: meu-tipo.yaml
name: Meu Tipo
slug: meu-tipo
description: "Descrição do tipo de projeto"
python_version: "3.8+"

supported_managers:
  - uv
  - pip

vscode_settings:
  python.linting.enabled: true

vscode_extensions:
  - ms-python.python

dependencies:
  core:
    - pacote-principal>=1.0
  dev:
    - pytest>=7.0

tags:
  - tag1
  - tag2

docs_url: "https://docs.example.com"
```

```bash
# 2. Validar YAML
python -c "from typysetup.core import ConfigLoader; loader = ConfigLoader(); loader.load_setup_type('meu-tipo')"

# 3. Testar
pytest tests/integration/test_setup_types.py
```

---

## Pull Requests

### Checklist Antes de Criar PR

- [ ] Código segue padrões de estilo (black, ruff)
- [ ] Testes adicionados/atualizados
- [ ] Todos os testes passam (`pytest`)
- [ ] Cobertura mantida/melhorada
- [ ] Documentação atualizada
- [ ] Commits seguem Conventional Commits
- [ ] Branch atualizada com main

### Template de PR

```markdown
## Descrição

Breve descrição do que foi mudado e por quê.

## Tipo de Mudança

- [ ] Bug fix (mudança que corrige um issue)
- [ ] Nova funcionalidade (mudança que adiciona funcionalidade)
- [ ] Breaking change (mudança que quebra compatibilidade)
- [ ] Documentação

## Como Foi Testado?

Descreva os testes que você executou:
- [ ] Unit tests
- [ ] Integration tests
- [ ] Manual testing

## Checklist

- [ ] Código segue padrões do projeto
- [ ] Self-review do código
- [ ] Comentários adicionados em código complexo
- [ ] Documentação atualizada
- [ ] Testes adicionados
- [ ] Todos os testes passam

## Screenshots (se aplicável)

[Adicione screenshots se a mudança afeta UI]
```

### Processo de Review

1. **Automated Checks**: CI/CD executa testes e linting
2. **Code Review**: Mantenedores revisam código
3. **Feedback**: Discussão e sugestões
4. **Aprovação**: PR aprovado para merge
5. **Merge**: Squash and merge para main

---

## Desenvolvimento Local

### Testando Mudanças Localmente

```bash
# Reinstalar em modo desenvolvimento após mudanças
pip install -e .

# Testar comando
typysetup setup /tmp/test-project --verbose

# Debugar com pdb
# Adicionar breakpoint no código:
import pdb; pdb.set_trace()

# Ou usar ipdb (mais features)
pip install ipdb
import ipdb; ipdb.set_trace()
```

### Debugging

```python
# Adicionar logging
import logging
logger = logging.getLogger(__name__)

def minha_funcao():
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
```

```bash
# Executar com logging habilitado
typysetup setup /tmp/test --verbose
```

---

## Perguntas Frequentes

### Como adiciono um novo comando CLI?

1. Criar arquivo em `src/typysetup/commands/`
2. Definir função com decorador `@app.command()`
3. Importar em `main.py`
4. Adicionar testes

### Como reporto um problema de segurança?

Envie email para [security@typysetup.dev] ao invés de criar issue pública.

### Como posso ajudar sem escrever código?

- Reportar bugs
- Melhorar documentação
- Responder issues de outros usuários
- Testar releases beta
- Traduzir documentação

---

## Recursos Adicionais

- **Documentação**: [docs/](docs/)
- **Architecture**: [ARCHITECTURE.md](docs/ARCHITECTURE.md)
- **Troubleshooting**: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **Typer Docs**: https://typer.tiangolo.com
- **Pydantic Docs**: https://docs.pydantic.dev
- **pytest Docs**: https://docs.pytest.org

---

## Licença

Ao contribuir, você concorda que suas contribuições serão licenciadas sob a MIT License.

---

**Obrigado por contribuir com TyPySetup!** 🎉

Se você tiver dúvidas, sinta-se à vontade para abrir uma issue ou entrar em contato com os mantenedores.
