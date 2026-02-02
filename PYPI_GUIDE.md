# Guia de Publicação no PyPI - TyPySetup

Guia completo para construir e publicar o TyPySetup no PyPI.

## Índice

1. [Pré-requisitos](#pré-requisitos)
2. [Construindo o Pacote](#construindo-o-pacote)
3. [Testando Localmente](#testando-localmente)
4. [Publicando no TestPyPI](#publicando-no-testpypi)
5. [Publicando no PyPI Produção](#publicando-no-pypi-produção)
6. [Gerenciamento de Versões](#gerenciamento-de-versões)
7. [Publicação Automatizada](#publicação-automatizada)
8. [Troubleshooting](#troubleshooting)

---

## Pré-requisitos

### Ferramentas Necessárias

```bash
# Instalar ferramentas de build
pip install build twine

# Verificar instalações
python -m build --version
twine --version
```

### Contas PyPI

1. **TestPyPI** (para testes)
   - Criar conta: https://test.pypi.org/account/register/
   - Verificar email

2. **PyPI** (produção)
   - Criar conta: https://pypi.org/account/register/
   - Verificar email
   - Habilitar 2FA (recomendado)

### Tokens de API

#### Criar Token TestPyPI

1. Fazer login em https://test.pypi.org/
2. Ir em Account Settings → API Tokens
3. Clicar "Add API Token"
4. Nome: `typysetup-upload`
5. Escopo: `Entire account` (primeiro upload) ou `Project: typysetup` (após primeiro upload)
6. Copiar token (começa com `pypi-`)
7. Guardar com segurança

#### Criar Token PyPI

1. Fazer login em https://pypi.org/
2. Ir em Account Settings → API Tokens
3. Clicar "Add API Token"
4. Nome: `typysetup-production`
5. Escopo: `Entire account` (primeiro upload) ou `Project: typysetup` (após primeiro upload)
6. Copiar token
7. Guardar com segurança

#### Armazenar Tokens Localmente

Criar `~/.pypirc`:

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-SEU_TOKEN_PYPI_AQUI

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-SEU_TOKEN_TESTPYPI_AQUI
```

Definir permissões:

```bash
chmod 600 ~/.pypirc
```

---

## Construindo o Pacote

### Passo 1: Checklist Pré-Build

```bash
# 1. Garantir que working tree está limpo
git status

# 2. Verificar versão
grep version pyproject.toml
grep __version__ src/typysetup/__init__.py

# 3. Executar testes
pytest

# 4. Verificar qualidade de código
black src/ tests/ --check
ruff check src/ tests/
mypy src/typysetup
```

### Passo 2: Limpar Builds Anteriores

```bash
# Remover artefatos antigos
rm -rf dist/
rm -rf build/
rm -rf src/*.egg-info

# Limpar cache Python
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
```

### Passo 3: Build do Pacote

```bash
# Build wheel e source distribution
python -m build

# Verificar saídas
ls -lh dist/
# Esperado:
# - typysetup-1.0.0-py3-none-any.whl
# - typysetup-1.0.0.tar.gz
```

### Passo 4: Inspecionar Conteúdo

```bash
# Inspecionar wheel
unzip -l dist/typysetup-1.0.0-py3-none-any.whl

# Inspecionar source distribution
tar -tzf dist/typysetup-1.0.0.tar.gz

# Verificar arquivos críticos incluídos:
# - src/typysetup/*.py
# - src/typysetup/configs/*.yaml
# - README.md
# - LICENSE
# - pyproject.toml
```

### Passo 5: Validar Metadados

```bash
# Validar pacote
twine check dist/*

# Deve retornar: "Checking dist/* PASSED"
```

---

## Testando Localmente

### Instalar do Build Local

```bash
# Criar ambiente virtual de teste
python -m venv test-venv
source test-venv/bin/activate  # Windows: test-venv\Scripts\activate

# Instalar do wheel
pip install dist/typysetup-1.0.0-py3-none-any.whl

# Testar CLI
typysetup --version  # Deve mostrar: 1.0.0
typysetup list
typysetup --help

# Testar setup em diretório temporário
mkdir /tmp/test-project
typysetup setup /tmp/test-project

# Limpar
deactivate
rm -rf test-venv
```

---

## Publicando no TestPyPI

### Por Que Testar no TestPyPI?

- Ambiente seguro de testes
- Idêntico ao PyPI de produção
- Pode ser deletado/resetado se encontrar problemas
- Sem impacto no pacote de produção

### Passo 1: Upload para TestPyPI

```bash
# Upload usando twine
twine upload --repository testpypi dist/*

# Saída esperada:
# Uploading distributions to https://test.pypi.org/legacy/
# Uploading typysetup-1.0.0-py3-none-any.whl
# Uploading typysetup-1.0.0.tar.gz
```

### Passo 2: Verificar no TestPyPI

1. Visitar: https://test.pypi.org/project/typysetup/
2. Verificar versão aparece corretamente
3. Conferir metadados, descrição, links
4. Verificar que README renderiza corretamente

### Passo 3: Testar Instalação do TestPyPI

```bash
# Criar ambiente virtual fresco
python -m venv testpypi-venv
source testpypi-venv/bin/activate

# Instalar do TestPyPI
# Nota: Use --extra-index-url para pegar dependências do PyPI real
pip install --index-url https://test.pypi.org/simple/ \
    --extra-index-url https://pypi.org/simple/ \
    typysetup

# Testar funcionalidade
typysetup --version
typysetup list
typysetup help

# Testar workflow completo
mkdir /tmp/testpypi-project
typysetup setup /tmp/testpypi-project

# Limpar
deactivate
rm -rf testpypi-venv
```

### Problemas Comuns TestPyPI

**Problema: Nome de pacote já existe**
- Solução: TestPyPI é compartilhado; escolher nome único ou usar sufixo

**Problema: Não é possível deletar versão**
- Solução: Incrementar número de versão (ex: 1.0.0.post1)

**Problema: Dependências não encontradas**
- Solução: Usar `--extra-index-url https://pypi.org/simple/`

---

## Publicando no PyPI Produção

### Checklist Final Pré-Voo

- [ ] Pacote testado no TestPyPI
- [ ] Instalação do TestPyPI funcionou
- [ ] Todas as funcionalidades testadas
- [ ] Documentação revisada
- [ ] Git tag criada e pushed
- [ ] CHANGELOG atualizado
- [ ] Sem mudanças não commitadas

### Passo 1: Upload para PyPI

```bash
# Upload para PyPI de produção
twine upload dist/*

# Saída esperada:
# Uploading distributions to https://upload.pypi.org/legacy/
# Uploading typysetup-1.0.0-py3-none-any.whl
# Uploading typysetup-1.0.0.tar.gz
```

### Passo 2: Verificar no PyPI

1. Visitar: https://pypi.org/project/typysetup/
2. Verificar todos os metadados corretos
3. Conferir renderização do README
4. Verificar links funcionam

### Passo 3: Testar Instalação do PyPI

```bash
# Criar ambiente fresco
python -m venv prod-test-venv
source prod-test-venv/bin/activate

# Instalar do PyPI
pip install typysetup

# Testar
typysetup --version  # Deve mostrar: 1.0.0
typysetup list
typysetup help

# Teste completo de workflow
mkdir /tmp/prod-test
typysetup setup /tmp/prod-test

# Limpar
deactivate
rm -rf prod-test-venv
```

### Passo 4: Criar GitHub Release

1. Ir para: https://github.com/mugubr/pysetup/releases
2. Clicar "Draft a new release"
3. Tag: v1.0.0
4. Título: TyPySetup v1.0.0 - Initial PyPI Release
5. Descrição: Copiar do CHANGELOG.md
6. Anexar dist/*.whl e dist/*.tar.gz
7. Publicar release

### Passo 5: Atualizar README com Badges

```markdown
[![PyPI version](https://badge.fury.io/py/typysetup.svg)](https://pypi.org/project/typysetup/)
[![Python versions](https://img.shields.io/pypi/pyversions/typysetup.svg)](https://pypi.org/project/typysetup/)
[![Downloads](https://pepy.tech/badge/typysetup)](https://pepy.tech/project/typysetup)
```

---

## Gerenciamento de Versões

### Semantic Versioning

TyPySetup segue [Semantic Versioning](https://semver.org/):

**Formato:** MAJOR.MINOR.PATCH

- **MAJOR**: Mudanças quebradoras (ex: 1.0.0 → 2.0.0)
- **MINOR**: Novas funcionalidades, compatível (ex: 1.0.0 → 1.1.0)
- **PATCH**: Correções de bugs (ex: 1.0.0 → 1.0.1)

### Processo de Atualização de Versão

#### Para Patch Release (Correções de Bugs)

```bash
# 1. Atualizar versão
sed -i 's/version = "1.0.0"/version = "1.0.1"/' pyproject.toml
sed -i 's/__version__ = "1.0.0"/__version__ = "1.0.1"/' src/typysetup/__init__.py

# 2. Atualizar CHANGELOG
# Adicionar entrada para [1.0.1]

# 3. Commit
git add pyproject.toml src/typysetup/__init__.py CHANGELOG.md
git commit -m "chore: bump version to 1.0.1"

# 4. Tag
git tag -a v1.0.1 -m "Release v1.0.1"
git push origin master
git push origin v1.0.1

# 5. Build e publicar
python -m build
twine upload --repository testpypi dist/*  # Testar primeiro
twine upload dist/*  # Depois produção
```

#### Para Minor Release (Novas Funcionalidades)

Mesmo processo, mas versão vira 1.1.0

#### Para Major Release (Breaking Changes)

Mesmo processo, mas versão vira 2.0.0

---

## Publicação Automatizada

### Visão Geral

Automatizar publicação no PyPI usando GitHub Actions quando tags são pushed.

### Configurar GitHub Secrets

1. Ir em repository settings → Secrets and variables → Actions
2. Adicionar secrets:
   - `PYPI_API_TOKEN`: Seu token de API do PyPI
   - `TESTPYPI_API_TOKEN`: Seu token de API do TestPyPI

### Usando o Workflow

```bash
# 1. Atualizar versão e commit
git add pyproject.toml src/typysetup/__init__.py CHANGELOG.md
git commit -m "chore: bump version to 1.1.0"
git push

# 2. Criar e push tag
git tag -a v1.1.0 -m "Release v1.1.0"
git push origin v1.1.0

# 3. GitHub Actions automaticamente:
#    - Builds do pacote
#    - Testa no TestPyPI
#    - Publica no PyPI
#    - Cria GitHub release
```

Acompanhar em: https://github.com/mugubr/pysetup/actions

---

## Troubleshooting

### Problemas de Build

**Erro: No module named 'build'**

```bash
pip install --upgrade build
```

**Erro: Package directory not found**

- Verificar `pyproject.toml` tem configuração correta de `packages`
- Confirmar estrutura de diretórios

**Erro: README not found**

- Garantir README.md existe na raiz
- Verificar `pyproject.toml` tem `readme = "README.md"`

### Problemas de Upload

**Erro: Invalid authentication credentials**

```bash
# Verificar formato do token (deve começar com pypi-)
# Regenerar token no PyPI/TestPyPI
# Atualizar ~/.pypirc com novo token
```

**Erro: File already exists**

- Não é possível re-upload da mesma versão
- Incrementar número de versão
- Ou usar `--skip-existing` (não recomendado para produção)

**Erro: Package name conflict**

- Primeiro upload ao PyPI reserva nome permanentemente
- Escolher nome diferente se já ocupado

### Problemas de Instalação

**Erro: Package not found após upload**

- Aguardar 1-2 minutos para indexação do PyPI
- Limpar cache do pip: `pip cache purge`
- Tentar: `pip install --no-cache-dir typysetup`

**Erro: Dependencies not installed**

- Verificar `pyproject.toml` dependências estão corretas
- Confirmar versões das dependências existem no PyPI

### Problemas de Versão

**Erro: Version mismatch**

```bash
# Garantir versão corresponde em todos os lugares:
grep version pyproject.toml
grep __version__ src/typysetup/__init__.py
git tag -l
```

---

## Melhores Práticas

### Pré-Release

1. Sempre testar no TestPyPI primeiro
2. Instalar e testar do TestPyPI antes de produção
3. Usar semantic versioning consistentemente
4. Manter CHANGELOG.md atualizado
5. Fazer tag de releases no git

### Segurança

1. Nunca commitar tokens de API no git
2. Usar tokens de API, não senhas
3. Habilitar 2FA na conta PyPI
4. Usar tokens com escopo de projeto quando possível
5. Rotacionar tokens periodicamente

### Qualidade

1. Executar suite completa de testes antes de publicar
2. Verificar qualidade de código (black, ruff, mypy)
3. Confirmar README renderiza corretamente no PyPI
4. Testar em ambiente virtual fresco
5. Manter dependências atualizadas

---

## Referência Rápida

### Comandos de Build

```bash
python -m build                    # Build do pacote
twine check dist/*                # Validar pacote
```

### Comandos de Upload

```bash
twine upload --repository testpypi dist/*   # Upload para TestPyPI
twine upload dist/*                         # Upload para PyPI
```

### Teste de Instalação

```bash
# Do TestPyPI
pip install --index-url https://test.pypi.org/simple/ \
    --extra-index-url https://pypi.org/simple/ typysetup

# Do PyPI
pip install typysetup
```

### Comandos de Limpeza

```bash
rm -rf dist/ build/ *.egg-info
find . -type d -name "__pycache__" -exec rm -rf {} +
```

---

## Recursos

- **PyPI**: https://pypi.org/
- **TestPyPI**: https://test.pypi.org/
- **Python Packaging Guide**: https://packaging.python.org/
- **Twine Documentation**: https://twine.readthedocs.io/
- **Build Documentation**: https://build.pypa.io/
- **Semantic Versioning**: https://semver.org/
- **GitHub Actions**: https://docs.github.com/actions

---

**Última atualização**: 2026-01-27
**Versão do guia**: 1.0.0
