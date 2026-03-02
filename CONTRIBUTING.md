# Guia de Contribuição - JusMonitorIA

Obrigado por considerar contribuir com o JusMonitorIA! Este documento fornece diretrizes para contribuir com o projeto.

## 📋 Índice

- [Código de Conduta](#código-de-conduta)
- [Como Posso Contribuir?](#como-posso-contribuir)
- [Configurando o Ambiente de Desenvolvimento](#configurando-o-ambiente-de-desenvolvimento)
- [Padrões de Código](#padrões-de-código)
- [Processo de Pull Request](#processo-de-pull-request)
- [Padrões de Commit](#padrões-de-commit)
- [Executando Testes](#executando-testes)
- [Reportando Bugs](#reportando-bugs)
- [Sugerindo Melhorias](#sugerindo-melhorias)

## 📜 Código de Conduta

### Nosso Compromisso

No interesse de promover um ambiente aberto e acolhedor, nós, como contribuidores e mantenedores, nos comprometemos a tornar a participação em nosso projeto e nossa comunidade uma experiência livre de assédio para todos.

### Nossos Padrões

Exemplos de comportamento que contribuem para criar um ambiente positivo incluem:

- Usar linguagem acolhedora e inclusiva
- Respeitar pontos de vista e experiências diferentes
- Aceitar críticas construtivas com elegância
- Focar no que é melhor para a comunidade
- Mostrar empatia com outros membros da comunidade

Exemplos de comportamento inaceitável incluem:

- Uso de linguagem ou imagens sexualizadas
- Comentários insultuosos/depreciativos e ataques pessoais ou políticos
- Assédio público ou privado
- Publicar informações privadas de outros sem permissão explícita
- Outras condutas que possam ser consideradas inadequadas em um ambiente profissional

## 🤝 Como Posso Contribuir?

### Reportar Bugs

Antes de criar um relatório de bug, verifique se o problema já não foi reportado. Se você encontrar um bug:

1. **Use o template de issue** para bugs
2. **Descreva o problema** claramente
3. **Forneça passos para reproduzir** o bug
4. **Inclua screenshots** se aplicável
5. **Especifique o ambiente** (OS, versão do Python/Node, etc.)

### Sugerir Melhorias

Se você tem uma ideia para melhorar o JusMonitorIA:

1. **Verifique se já não existe** uma issue similar
2. **Use o template de issue** para features
3. **Descreva a funcionalidade** desejada
4. **Explique o caso de uso** e o problema que resolve
5. **Forneça mockups** se aplicável

### Contribuir com Código

1. **Fork** o repositório
2. **Clone** seu fork localmente
3. **Crie uma branch** para sua feature/fix
4. **Faça suas alterações** seguindo os padrões de código
5. **Escreva testes** para suas alterações
6. **Execute os testes** e garanta que passam
7. **Commit** suas mudanças seguindo os padrões de commit
8. **Push** para sua branch
9. **Abra um Pull Request**

## 🛠️ Configurando o Ambiente de Desenvolvimento

### Pré-requisitos

- Docker 24+ e Docker Compose 2.20+
- Python 3.12+ (para desenvolvimento local)
- Node.js 20+ e npm 10+ (para desenvolvimento local)
- Poetry 1.7+ (gerenciador de dependências Python)
- Git

### Setup Rápido

```bash
# 1. Fork e clone o repositório
git clone https://github.com/seu-usuario/jusmonitoria.git
cd jusmonitoria

# 2. Configure variáveis de ambiente
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local

# 3. Edite os arquivos .env com suas credenciais
# Mínimo necessário:
# - SECRET_KEY (gerar com: openssl rand -hex 32)
# - JWT_SECRET_KEY (gerar com: openssl rand -hex 32)
# - OPENAI_API_KEY (obter em https://platform.openai.com)

# 4. Inicie o ambiente de desenvolvimento
./scripts/dev.sh

# 5. (Opcional) Popular banco com dados de teste
./scripts/seed.sh --all
```

### Desenvolvimento Local (Sem Docker)

#### Backend

```bash
cd backend

# Instalar dependências
poetry install

# Ativar ambiente virtual
poetry shell

# Configurar .env
cp .env.example .env
nano .env

# Aplicar migrations
alembic upgrade head

# Iniciar servidor
uvicorn app.main:app --reload

# Em outro terminal, iniciar workers
taskiq worker app.workers.broker:broker --reload
```

#### Frontend

```bash
cd frontend

# Instalar dependências
npm install

# Configurar .env
cp .env.example .env.local
nano .env.local

# Iniciar servidor de desenvolvimento
npm run dev
```

## 📝 Padrões de Código

### Backend (Python)

#### Estilo de Código

Seguimos [PEP 8](https://pep8.org/) com algumas customizações:

- **Comprimento de linha**: 100 caracteres (não 79)
- **Imports**: Organizados em 3 grupos (stdlib, third-party, local)
- **Type hints**: Obrigatórios em todas as funções públicas
- **Docstrings**: Formato Google para todas as funções/classes públicas

#### Ferramentas

```bash
# Linting com Ruff
poetry run ruff check .

# Auto-fix
poetry run ruff check --fix .

# Formatação com Black
poetry run black .

# Type checking com mypy
poetry run mypy app/
```

#### Exemplo de Código

```python
"""Module docstring describing the module."""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.client import Client
from app.db.repositories.base import BaseRepository


class ClientCreate(BaseModel):
    """Schema for creating a client."""
    
    full_name: str
    cpf_cnpj: str
    email: Optional[str] = None
    phone: Optional[str] = None


class ClientRepository(BaseRepository[Client]):
    """Repository for client operations."""
    
    async def get_by_cpf(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        cpf_cnpj: str,
    ) -> Optional[Client]:
        """
        Get client by CPF/CNPJ.
        
        Args:
            session: Database session
            tenant_id: Tenant ID for isolation
            cpf_cnpj: CPF or CNPJ to search
            
        Returns:
            Client if found, None otherwise
        """
        # Implementation here
        pass
```

#### Convenções de Nomenclatura

- **Variáveis e funções**: `snake_case`
- **Classes**: `PascalCase`
- **Constantes**: `UPPER_SNAKE_CASE`
- **Privado**: Prefixo `_` (ex: `_internal_function`)
- **Arquivos**: `snake_case.py`

### Frontend (TypeScript/React)

#### Estilo de Código

Seguimos [Airbnb JavaScript Style Guide](https://github.com/airbnb/javascript) com TypeScript:

- **Comprimento de linha**: 100 caracteres
- **Indentação**: 2 espaços
- **Aspas**: Simples para strings, duplas para JSX
- **Ponto e vírgula**: Obrigatório
- **Trailing comma**: Sempre

#### Ferramentas

```bash
# Linting com ESLint
npm run lint

# Auto-fix
npm run lint:fix

# Formatação com Prettier
npm run format

# Type checking
npm run type-check
```

#### Exemplo de Código

```typescript
// components/clients/ClientCard.tsx

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Client } from '@/types';

interface ClientCardProps {
  client: Client;
  onSelect?: (client: Client) => void;
}

export function ClientCard({ client, onSelect }: ClientCardProps) {
  const handleClick = () => {
    onSelect?.(client);
  };

  return (
    <Card className="cursor-pointer hover:shadow-lg" onClick={handleClick}>
      <CardHeader>
        <CardTitle>{client.full_name}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">{client.email}</span>
          <Badge variant={client.status === 'active' ? 'default' : 'secondary'}>
            {client.status}
          </Badge>
        </div>
      </CardContent>
    </Card>
  );
}
```

#### Convenções de Nomenclatura

- **Componentes**: `PascalCase` (ex: `ClientCard.tsx`)
- **Hooks**: `camelCase` com prefixo `use` (ex: `useAuth.ts`)
- **Utilitários**: `camelCase` (ex: `formatDate.ts`)
- **Tipos/Interfaces**: `PascalCase` (ex: `Client`, `ClientProps`)
- **Constantes**: `UPPER_SNAKE_CASE`

#### Estrutura de Componentes

```
components/
├── ui/              # Componentes base (Shadcn/UI)
├── dashboard/       # Componentes específicos do dashboard
├── funil/           # Componentes do funil
├── prontuario/      # Componentes do prontuário
└── layout/          # Componentes de layout
```

## 🔄 Processo de Pull Request

### Antes de Abrir um PR

1. ✅ Certifique-se que seu código segue os padrões
2. ✅ Execute os testes e garanta que passam
3. ✅ Atualize a documentação se necessário
4. ✅ Adicione testes para novas funcionalidades
5. ✅ Verifique se não há conflitos com a branch `main`

### Abrindo um PR

1. **Título descritivo**: Use o formato de Conventional Commits
   - `feat: adiciona busca semântica de processos`
   - `fix: corrige cálculo de score de leads`
   - `docs: atualiza README com instruções de deploy`

2. **Descrição completa**: Use o template de PR
   - O que foi alterado?
   - Por que foi alterado?
   - Como testar?
   - Screenshots (se aplicável)

3. **Link para issue**: Se o PR resolve uma issue, referencie-a
   - `Closes #123`
   - `Fixes #456`

4. **Labels apropriados**: Adicione labels relevantes
   - `bug`, `enhancement`, `documentation`, etc.

### Template de PR

```markdown
## Descrição

Breve descrição das alterações.

## Tipo de Mudança

- [ ] Bug fix (mudança que corrige um problema)
- [ ] Nova funcionalidade (mudança que adiciona funcionalidade)
- [ ] Breaking change (mudança que quebra compatibilidade)
- [ ] Documentação (mudança apenas em documentação)

## Como Testar

1. Passo 1
2. Passo 2
3. Passo 3

## Checklist

- [ ] Meu código segue os padrões do projeto
- [ ] Realizei self-review do meu código
- [ ] Comentei código complexo quando necessário
- [ ] Atualizei a documentação
- [ ] Minhas mudanças não geram novos warnings
- [ ] Adicionei testes que provam que minha correção/feature funciona
- [ ] Testes unitários novos e existentes passam localmente
- [ ] Mudanças dependentes foram mergeadas

## Screenshots (se aplicável)

Adicione screenshots para mudanças visuais.

## Issues Relacionadas

Closes #123
```

### Code Review

Todos os PRs passam por code review. Esperamos:

- ✅ Código limpo e legível
- ✅ Testes adequados
- ✅ Documentação atualizada
- ✅ Sem vulnerabilidades de segurança
- ✅ Performance não degradada
- ✅ Compatibilidade mantida

### Após Aprovação

1. **Squash commits** se houver muitos commits pequenos
2. **Merge** será feito por um mantenedor
3. **Delete branch** após merge

## 📝 Padrões de Commit

Seguimos [Conventional Commits](https://www.conventionalcommits.org/):

### Formato

```
<tipo>(<escopo>): <descrição>

[corpo opcional]

[rodapé opcional]
```

### Tipos

- `feat`: Nova funcionalidade
- `fix`: Correção de bug
- `docs`: Alterações na documentação
- `style`: Formatação, ponto e vírgula, etc (sem mudança de código)
- `refactor`: Refatoração de código
- `perf`: Melhoria de performance
- `test`: Adição ou correção de testes
- `chore`: Tarefas de manutenção, dependências, etc
- `ci`: Mudanças em CI/CD
- `build`: Mudanças no sistema de build

### Exemplos

```bash
# Feature
feat(leads): adiciona filtro por score no funil

# Bug fix
fix(auth): corrige validação de token expirado

# Documentação
docs(api): adiciona exemplos de uso de webhooks

# Refatoração
refactor(dashboard): extrai lógica de métricas para service

# Teste
test(clients): adiciona testes para prontuário 360º

# Breaking change
feat(api)!: altera formato de resposta de paginação

BREAKING CHANGE: O campo 'count' foi renomeado para 'total'
```

### Regras

- Use o imperativo ("adiciona" não "adicionado")
- Primeira linha com no máximo 72 caracteres
- Corpo opcional para explicar o "porquê" (não o "como")
- Rodapé para breaking changes e referências a issues

## 🧪 Executando Testes

### Backend

```bash
cd backend

# Todos os testes
poetry run pytest

# Com cobertura
poetry run pytest --cov=app --cov-report=html --cov-report=term

# Apenas testes unitários
poetry run pytest tests/unit/

# Apenas testes de integração
poetry run pytest tests/integration/

# Apenas property-based tests
poetry run pytest tests/property/

# Testes específicos
poetry run pytest tests/unit/test_auth.py

# Modo verbose
poetry run pytest -v

# Parar no primeiro erro
poetry run pytest -x
```

### Frontend

```bash
cd frontend

# Linting
npm run lint

# Type checking
npm run type-check

# Formatação
npm run format:check
```

### Usando Scripts

```bash
# Executar todos os testes (backend + frontend)
./scripts/test.sh

# Apenas backend
./scripts/test.sh --backend-only

# Apenas frontend
./scripts/test.sh --frontend-only

# Com cobertura
./scripts/test.sh --coverage
```

### Cobertura de Código

Mantemos cobertura mínima de **80%** para o backend.

```bash
# Gerar relatório de cobertura
poetry run pytest --cov=app --cov-report=html

# Abrir relatório no navegador
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

## 🐛 Reportando Bugs

### Antes de Reportar

1. **Verifique se já não foi reportado** na lista de issues
2. **Tente reproduzir** em ambiente limpo
3. **Colete informações** sobre o ambiente

### Template de Bug Report

```markdown
## Descrição do Bug

Descrição clara e concisa do bug.

## Passos para Reproduzir

1. Vá para '...'
2. Clique em '...'
3. Role até '...'
4. Veja o erro

## Comportamento Esperado

Descrição clara do que deveria acontecer.

## Comportamento Atual

Descrição clara do que está acontecendo.

## Screenshots

Se aplicável, adicione screenshots.

## Ambiente

- OS: [ex: Ubuntu 22.04]
- Browser: [ex: Chrome 120]
- Versão do Python: [ex: 3.12.1]
- Versão do Node: [ex: 20.10.0]
- Versão do Docker: [ex: 24.0.7]

## Logs

```
Cole logs relevantes aqui
```

## Contexto Adicional

Qualquer outra informação relevante.
```

## 💡 Sugerindo Melhorias

### Template de Feature Request

```markdown
## Problema

Descrição clara do problema que a feature resolve.

## Solução Proposta

Descrição clara da solução desejada.

## Alternativas Consideradas

Descrição de soluções alternativas que você considerou.

## Mockups/Exemplos

Se aplicável, adicione mockups ou exemplos.

## Contexto Adicional

Qualquer outra informação relevante.
```

## 📚 Recursos Adicionais

### Documentação

- [README Principal](README.md)
- [Documentação da API](docs/api.md)
- [Backend README](backend/README.md)
- [Frontend README](frontend/README.md)

### Tutoriais

- [Como criar um novo agente de IA](docs/tutorials/create-ai-agent.md)
- [Como adicionar um novo endpoint](docs/tutorials/create-endpoint.md)
- [Como configurar ambiente de desenvolvimento](docs/tutorials/dev-setup.md)

### Links Úteis

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Next.js Documentation](https://nextjs.org/docs)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Taskiq Documentation](https://taskiq-python.github.io/)

## 🙏 Agradecimentos

Obrigado por contribuir com o JusMonitorIA! Sua ajuda é muito apreciada.

Se você tiver dúvidas, não hesite em:

- Abrir uma issue
- Entrar em contato via email: dev@jusmonitoria.com
- Participar das discussões no Slack (interno)

---

**Desenvolvido com ❤️ pela equipe JusMonitorIA**
