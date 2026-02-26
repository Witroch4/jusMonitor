# Guia Completo: Configuração Kiro + WSL + MCP

> Guia end-to-end para configurar Kiro com Windows Subsystem for Linux (WSL) e Model Context Protocol (MCP) em qualquer máquina Windows.

## 📋 Pré-requisitos

- Windows 10/11 com WSL2 instalado
- Ubuntu (ou outra distro Linux) no WSL
- Kiro instalado no Windows
- Acesso a terminal PowerShell (como Administrador para alguns comandos)

---

## 🚀 Passo 1: Instalar Git for Windows

O Kiro precisa do Git instalado no Windows para integração completa.

### Opção A: Download Manual
1. Acesse: https://git-scm.com/download/win
2. Baixe e instale a versão mais recente
3. Use as configurações padrão durante a instalação

### Opção B: Via Kiro
1. Abra o Kiro
2. Vá para o painel Git
3. Clique no botão "Download Git"
4. Siga as instruções

---

## 🔧 Passo 2: Configurar Git para WSL

**IMPORTANTE**: Execute no PowerShell do Windows (não no WSL)

```powershell
# Permitir repositórios com owners diferentes (necessário para WSL)
git config --global --add safe.directory '*'
```

**Por quê?** Quando o Kiro (Windows) acessa arquivos do WSL, o owner é diferente. Esta configuração evita erros de "unsafe repository".

---

## 🐍 Passo 3: Instalar `uv` no WSL

O `uv` é um gerenciador de pacotes Python rápido, necessário para rodar servidores MCP.

**Execute no terminal WSL:**

```bash
# Instalar uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Adicionar ao PATH (se necessário)
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Verificar instalação
which uvx
# Deve retornar: /home/seu-usuario/.local/bin/uvx
```

---

## ⚙️ Passo 4: Configurar MCP Global

Crie a configuração MCP global que será usada em todos os projetos.

### Método A: Via PowerShell (Recomendado)

**Execute no PowerShell do Windows:**

```powershell
# Criar diretório se não existir
mkdir $env:USERPROFILE\.kiro\settings -Force

# Criar arquivo de configuração
@"
{
	"mcpServers": {
		"fetch": {
			"command": "wsl.exe",
			"args": ["--shell-type", "login", "uvx", "mcp-server-fetch"],
			"env": {},
			"disabled": false,
			"autoApprove": ["fetch"]
		}
	}
}
"@ | Out-File -FilePath "$env:USERPROFILE\.kiro\settings\mcp.json" -Encoding UTF8
```

### Método B: Manual

1. Navegue até: `C:\Users\SEU-USUARIO\.kiro\settings\`
2. Crie/edite o arquivo `mcp.json`
3. Cole o seguinte conteúdo:

```json
{
	"mcpServers": {
		"fetch": {
			"command": "wsl.exe",
			"args": ["--shell-type", "login", "uvx", "mcp-server-fetch"],
			"env": {},
			"disabled": false,
			"autoApprove": ["fetch"]
		}
	}
}
```

### O que esta configuração faz?

- **`wsl.exe`**: Executa comandos no WSL a partir do Windows
- **`--shell-type login`**: Usa login shell (carrega PATH e variáveis de ambiente)
- **`uvx mcp-server-fetch`**: Roda o servidor MCP fetch via uv
- **`disabled: false`**: Servidor habilitado
- **`autoApprove: ["fetch"]`**: Auto-aprova chamadas do fetch (sem popup)

---

## 🎯 Passo 5: Abrir Projeto no Kiro via WSL

### Método 1: Via Terminal WSL (Recomendado)

```bash
# No terminal WSL, navegue até seu projeto
cd ~/seu-projeto

# Abra o Kiro
kiro .
```

O Kiro vai abrir no Windows e automaticamente conectar ao WSL.

### Método 2: Via Kiro (Windows)

1. Abra o Kiro
2. `File → Open Folder`
3. Digite: `\\wsl$\Ubuntu\home\seu-usuario\seu-projeto`
4. Ou navegue manualmente pelo explorador

### Método 3: Command Palette

1. `Ctrl+Shift+P`
2. Digite: `Remote-WSL: Open Folder in WSL`
3. Selecione o projeto

---

## ✅ Passo 6: Verificar Configuração

### 6.1 Verificar MCP Servers

1. Abra o Kiro
2. Vá para o painel lateral → **MCP SERVERS**
3. Verifique se aparecem:
   - ✅ **fetch** - Connected (1 tool)
   - ✅ **GitKraken** - Connected (23 tools) *(se tiver GitLens instalado)*
   - ✅ **shadcn** - Connected (7 tools) *(se configurado)*

### 6.2 Verificar Terminal WSL

Abra o terminal integrado no Kiro (`Ctrl+``) e execute:

```bash
# Verificar que está no WSL
pwd
# Deve mostrar caminho Linux: /home/seu-usuario/projeto

uname -a
# Deve mostrar: Linux

# Verificar ferramentas
which node
which npm
which python3
which uvx
```

### 6.3 Testar MCP Fetch

No chat do Kiro, teste:

```
Busque informações sobre Next.js 15
```

O Kiro deve usar o servidor MCP fetch para buscar informações atualizadas da web.

---

## 🎨 Passo 7: Configurações Opcionais

### 7.1 Adicionar Mais Servidores MCP

Edite `C:\Users\SEU-USUARIO\.kiro\settings\mcp.json`:

```json
{
	"mcpServers": {
		"fetch": {
			"command": "wsl.exe",
			"args": ["--shell-type", "login", "uvx", "mcp-server-fetch"],
			"env": {},
			"disabled": false,
			"autoApprove": ["fetch"]
		},
		"filesystem": {
			"command": "wsl.exe",
			"args": ["--shell-type", "login", "uvx", "mcp-server-filesystem"],
			"env": {},
			"disabled": false,
			"autoApprove": []
		},
		"postgres": {
			"command": "wsl.exe",
			"args": ["--shell-type", "login", "uvx", "mcp-server-postgres"],
			"env": {
				"POSTGRES_CONNECTION_STRING": "postgresql://user:pass@localhost:5432/db"
			},
			"disabled": false,
			"autoApprove": []
		}
	}
}
```

### 7.2 Criar Alias no WSL

Facilite a abertura do Kiro:

```bash
# Adicionar ao ~/.bashrc
echo 'alias k="kiro ."' >> ~/.bashrc
source ~/.bashrc

# Agora você pode fazer:
cd ~/projeto
k  # Abre o Kiro no projeto atual
```

### 7.3 Configurar Git no WSL

```bash
# Configurar identidade
git config --global user.name "Seu Nome"
git config --global user.email "seu@email.com"

# Configurar editor padrão
git config --global core.editor "nano"
```

---

## 🔍 Troubleshooting

### Problema: MCP fetch não conecta

**Solução:**

```bash
# No WSL, verificar se uv está instalado
which uvx

# Se não estiver, reinstalar
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc
```

### Problema: Git "unsafe repository"

**Solução:**

```powershell
# No PowerShell do Windows
git config --global --add safe.directory '*'
```

### Problema: Terminal não abre no WSL

**Solução:**

1. Verifique se o projeto foi aberto via WSL (`\\wsl$\...`)
2. Reinicie o Kiro
3. Abra o projeto novamente via `kiro .` no terminal WSL

### Problema: Comandos não encontrados no WSL

**Solução:**

```bash
# Verificar PATH
echo $PATH

# Adicionar ao ~/.bashrc se necessário
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### Problema: MCP server "disabled"

**Solução:**

Edite `C:\Users\SEU-USUARIO\.kiro\settings\mcp.json` e mude:

```json
"disabled": false  // Deve ser false, não true
```

---

## 📚 Referências

- **Kiro + WSL**: https://docs.kiro.ai/wsl
- **MCP Protocol**: https://modelcontextprotocol.io
- **uv Package Manager**: https://docs.astral.sh/uv/
- **WSL Documentation**: https://learn.microsoft.com/windows/wsl/

---

## 🎯 Checklist Rápido

Use este checklist ao configurar uma nova máquina:

- [ ] WSL2 instalado e configurado
- [ ] Git for Windows instalado
- [ ] `git config --global --add safe.directory '*'` executado
- [ ] `uv` instalado no WSL (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- [ ] `uvx` no PATH do WSL (`which uvx` retorna caminho)
- [ ] `mcp.json` criado em `C:\Users\SEU-USUARIO\.kiro\settings\`
- [ ] Kiro reiniciado
- [ ] MCP servers conectados (verificar painel MCP)
- [ ] Terminal integrado abre no WSL (`pwd` mostra caminho Linux)
- [ ] Teste MCP fetch funcionando

---

## 💡 Dicas Pro

1. **Sempre abra projetos via WSL**: Use `kiro .` no terminal WSL para garantir integração correta

2. **Use caminhos WSL no Windows**: `\\wsl$\Ubuntu\home\usuario\projeto`

3. **Mantenha ferramentas no WSL**: Instale Node, Python, etc. apenas no WSL, não no Windows

4. **Backup da configuração**: Salve `C:\Users\SEU-USUARIO\.kiro\settings\mcp.json` em um repositório Git

5. **Múltiplas distros WSL**: Se usar várias distros, ajuste o caminho: `\\wsl$\Debian\...` ou `\\wsl$\Ubuntu-22.04\...`

---

## 🚀 Próximos Passos

Após configurar tudo:

1. Explore os servidores MCP disponíveis: https://github.com/modelcontextprotocol/servers
2. Configure servidores específicos para seu stack (Postgres, Redis, etc.)
3. Crie workflows personalizados no Kiro
4. Configure hooks e automações

---

**Última atualização**: 2026-02-23  
**Testado em**: Windows 11 + WSL2 (Ubuntu 22.04) + Kiro v1.x

---

## 📝 Notas de Versão

### v1.0 (2026-02-23)
- Guia inicial completo
- Configuração MCP com WSL
- Troubleshooting básico
- Checklist de verificação

---

**Contribuições**: Se encontrar problemas ou melhorias, documente aqui para referência futura.
