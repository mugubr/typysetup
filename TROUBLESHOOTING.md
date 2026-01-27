# Troubleshooting Guide

Este guia ajuda a resolver problemas comuns ao usar o TyPySetup CLI.

## Índice

- [Instalação](#instalação)
- [Virtual Environment](#virtual-environment)
- [Instalação de Dependências](#instalação-de-dependências)
- [VSCode Integration](#vscode-integration)
- [Preferências](#preferências)
- [Plataforma Específica](#plataforma-específica)
- [Performance](#performance)

---

## Instalação

### Problema: `typysetup: command not found`

**Causa**: O comando typysetup não está no PATH ou não foi instalado corretamente.

**Soluções**:

```bash
# 1. Verificar se foi instalado
pip show typysetup

# 2. Se não estiver instalado, instalar
pip install typysetup

# 3. Se instalou mas comando não é encontrado, adicionar ao PATH
# Linux/macOS (adicionar ao ~/.bashrc ou ~/.zshrc)
export PATH="$HOME/.local/bin:$PATH"

# Windows - adicionar manualmente ao PATH do sistema
# ou reinstalar com:
pip install --user typysetup
```

### Problema: `ModuleNotFoundError: No module named 'typysetup'`

**Causa**: TyPySetup não está instalado no ambiente Python atual.

**Solução**:
```bash
# Verificar ambiente Python ativo
which python
python --version

# Instalar no ambiente correto
pip install typysetup

# Ou instalar no modo de desenvolvimento
git clone https://github.com/user/typysetup
cd typysetup
pip install -e .
```

---

## Virtual Environment

### Problema: Falha ao criar virtual environment

**Erro**: `Error: Failed to create virtual environment`

**Causas e Soluções**:

1. **Python não instalado ou versão incompatível**
   ```bash
   # Verificar versão do Python
   python --version  # Deve ser 3.8+

   # Instalar Python 3.8+ se necessário
   # Ubuntu/Debian
   sudo apt install python3.11

   # macOS
   brew install python@3.11
   ```

2. **Permissões insuficientes**
   ```bash
   # Verificar permissões do diretório
   ls -la /path/to/project

   # Criar diretório com permissões corretas
   mkdir -p /path/to/project
   chmod 755 /path/to/project
   ```

3. **Espaço em disco insuficiente**
   ```bash
   # Verificar espaço disponível
   df -h

   # Limpar cache do pip se necessário
   pip cache purge
   ```

### Problema: Virtual environment criado mas Python não funciona

**Erro**: `venv/bin/python: No such file or directory`

**Solução**:
```bash
# No Windows, use Scripts ao invés de bin
venv\Scripts\python.exe

# Recriar virtual environment
rm -rf venv
typysetup setup /path/to/project
```

---

## Instalação de Dependências

### Problema: `uv not found`

**Causa**: uv não está instalado no sistema.

**Soluções**:

```bash
# Opção 1: Instalar uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Opção 2: Usar pip como alternativa
# Durante setup, selecione "pip" como package manager

# Opção 3: Instalar uv via pip
pip install uv
```

### Problema: Timeout durante instalação de dependências

**Erro**: `HTTPSConnectionPool... Read timed out`

**Soluções**:

```bash
# 1. Tentar novamente (problemas de rede temporários)
typysetup setup /path/to/project

# 2. Aumentar timeout do pip
pip install --timeout 300 <package>

# 3. Usar mirror PyPI alternativo
pip install --index-url https://pypi.org/simple <package>

# 4. Instalar manualmente depois
cd /path/to/project
source venv/bin/activate
pip install -r requirements.txt
```

### Problema: Package não encontrado

**Erro**: `ERROR: Could not find a version that satisfies the requirement <package>`

**Soluções**:

```bash
# 1. Verificar nome correto do pacote
pip search <package>

# 2. Verificar se existe para sua versão do Python
# Alguns pacotes não suportam Python 3.12, por exemplo

# 3. Instalar manualmente uma versão específica
pip install <package>==<version>

# 4. Editar YAML do setup type e remover/substituir pacote problemático
```

---

## VSCode Integration

### Problema: VSCode não reconhece virtual environment

**Sintoma**: VSCode mostra imports como não resolvidos, mas funcionam no terminal.

**Soluções**:

1. **Recarregar VSCode**
   - Pressione `Ctrl+Shift+P` (ou `Cmd+Shift+P` no macOS)
   - Digite "Developer: Reload Window"

2. **Selecionar interpretador correto**
   - `Ctrl+Shift+P` → "Python: Select Interpreter"
   - Escolha `./venv/bin/python`

3. **Verificar settings.json**
   ```bash
   cat .vscode/settings.json
   # Deve conter:
   # "python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python"
   ```

4. **Regenerar configuração**
   ```bash
   rm -rf .vscode
   typysetup setup . --verbose
   ```

### Problema: Extensions não são recomendadas automaticamente

**Solução**:

1. Verificar `.vscode/extensions.json`:
   ```bash
   cat .vscode/extensions.json
   ```

2. Instalar extensões manualmente:
   - Abrir VSCode
   - `Ctrl+Shift+X` para Extensions
   - Procurar e instalar: `ms-python.python`, `ms-python.vscode-pylance`, etc.

3. Aceitar recomendações do VSCode quando aparecerem no canto inferior direito

---

## Preferências

### Problema: Preferências não são salvas

**Erro**: `PermissionError: [Errno 13] Permission denied: '~/.typysetup/preferences.json'`

**Soluções**:

```bash
# 1. Criar diretório com permissões corretas
mkdir -p ~/.typysetup
chmod 755 ~/.typysetup

# 2. Verificar propriedade do arquivo
ls -la ~/.typysetup/preferences.json
chown $USER:$USER ~/.typysetup/preferences.json

# 3. Resetar preferências
rm ~/.typysetup/preferences.json
typysetup preferences --show  # Recria com defaults
```

### Problema: Preferências corrompidas

**Erro**: `JSONDecodeError: Expecting value`

**Solução**:
```bash
# Fazer backup e resetar
mv ~/.typysetup/preferences.json ~/.typysetup/preferences.json.backup
typysetup preferences --reset

# Ou editar manualmente
vim ~/.typysetup/preferences.json
```

---

## Plataforma Específica

### Windows: `'source' is not recognized`

**Problema**: Comando source não existe no Windows.

**Solução**:
```powershell
# PowerShell
venv\Scripts\Activate.ps1

# CMD
venv\Scripts\activate.bat

# Git Bash no Windows
source venv/Scripts/activate
```

### Windows: Script execution policy error

**Erro**: `... cannot be loaded because running scripts is disabled`

**Solução**:
```powershell
# Executar como Administrador
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Ou usar bypass temporário
powershell -ExecutionPolicy Bypass -File script.ps1
```

### macOS: SSL Certificate error

**Erro**: `SSL: CERTIFICATE_VERIFY_FAILED`

**Solução**:
```bash
# Instalar certificados Python
/Applications/Python\ 3.x/Install\ Certificates.command

# Ou atualizar certifi
pip install --upgrade certifi
```

---

## Performance

### Problema: Setup muito lento (>5 minutos)

**Diagnóstico**:
```bash
# Executar com verbose para ver onde está demorando
typysetup setup /path/to/project --verbose
```

**Otimizações**:

1. **Usar uv ao invés de pip** (10-100x mais rápido)
   ```bash
   # Instalar uv se ainda não tiver
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Reduzir dependências opcionais**
   - Durante setup, desmarcar dependências opcionais

3. **Usar cache local**
   ```bash
   # pip
   pip install --cache-dir ~/.cache/pip

   # uv usa cache automaticamente
   ```

4. **Setup types muito grandes** (ML/AI com TensorFlow/PyTorch)
   - É normal demorar 2-5 minutos
   - Considere usar Docker ao invés

---

## Problemas Comuns Gerais

### Problema: Setup interrompido no meio

**O que fazer**:

1. **Verificar se venv foi criado**
   ```bash
   ls -la /path/to/project/venv
   ```

2. **Limpar e tentar novamente**
   ```bash
   rm -rf /path/to/project/venv
   rm -rf /path/to/project/.vscode
   typysetup setup /path/to/project
   ```

3. **Rollback foi executado automaticamente**
   - TyPySetup limpa automaticamente em caso de falha
   - Seguro tentar novamente

### Problema: Versão do Python incompatível

**Erro**: `This setup type requires Python 3.10+, but you have 3.8`

**Soluções**:

1. **Instalar versão mais recente do Python**
   ```bash
   # Ubuntu/Debian
   sudo apt install python3.11

   # macOS
   brew install python@3.11

   # Ou usar pyenv
   pyenv install 3.11.0
   pyenv global 3.11.0
   ```

2. **Escolher setup type compatível**
   - Alguns tipos (FastAPI, async-realtime) requerem Python 3.10+
   - Outros (Django, CLI tools) funcionam com Python 3.8+

---

## Debug Avançado

### Habilitar logging detalhado

```bash
# Modo verbose
typysetup setup /path/to/project --verbose

# Logs completos
export PYSETUP_LOG_LEVEL=DEBUG
typysetup setup /path/to/project
```

### Verificar configuração gerada

```bash
# Ver configuração do projeto
typysetup config /path/to/project

# Ver preferências do usuário
typysetup preferences --show

# Ver histórico de setups
typysetup history --verbose
```

### Reportar problemas

Se nenhuma solução funcionou:

1. **Coletar informações**:
   ```bash
   python --version
   pip --version
   typysetup --version
   uname -a  # Linux/macOS
   ```

2. **Executar com verbose**:
   ```bash
   typysetup setup /path/to/project --verbose > debug.log 2>&1
   ```

3. **Criar issue** no repositório com:
   - Versões (Python, typysetup, OS)
   - Log completo (debug.log)
   - Passos para reproduzir

---

## Recursos Adicionais

- **Documentação**: [README.md](README.md)
- **Arquitetura**: [ARCHITECTURE.md](docs/ARCHITECTURE.md)
- **Contribuir**: [CONTRIBUTING.md](CONTRIBUTING.md)
- **Changelog**: [CHANGELOG.md](CHANGELOG.md)

---

**Última atualização**: 2026-01-25
