# Plano de Implementação: JusMonitor CRM Orquestrador

## Visão Geral

Este plano implementa um sistema completo de CRM jurídico com orquestração de IA, integrações com Chatwit e DataJud, e arquitetura multi-tenant. A implementação segue Clean Architecture com backend FastAPI + Python e frontend Next.js 16 + TypeScript.

## Tarefas

- [x] 1. Configurar infraestrutura base e ambiente de desenvolvimento
  - [x] 1.1 Criar estrutura de diretórios do projeto
    - Criar diretórios: backend/, frontend/, docker/, docs/
    - Criar backend/: api/, core/, db/, services/, workers/, tests/
    - Criar frontend/: app/, components/, lib/, hooks/
    - _Requisitos: Todos (base do projeto)_
  
  - [x] 1.2 Configurar Docker Compose com serviços base
    - Criar docker-compose.yml com PostgreSQL 17, Redis, pgvector
    - Configurar redes isoladas (backend-net, db-net)
    - Configurar volumes persistentes
    - Adicionar healthchecks para todos os serviços
    - _Requisitos: 1.1, 2.1, 3.1_
  
  - [x] 1.3 Configurar ambiente Python do backend
    - Criar pyproject.toml com Poetry
    - Adicionar dependências: fastapi, sqlalchemy[asyncio], asyncpg, pydantic, taskiq, langchain, litellm
    - Configurar pytest, ruff, mypy
    - Criar .env.example com variáveis de ambiente
    - _Requisitos: Todos (base técnica)_
  
  - [x] 1.4 Configurar ambiente Next.js do frontend
    - Executar create-next-app com App Router e TypeScript
    - Configurar Tailwind CSS e Shadcn/UI
    - Adicionar dependências: react-query, zustand, zod
    - Configurar ESLint e Prettier
    - _Requisitos: 4.1, 4.2, 4.3_

- [x] 2. Implementar camada de dados e modelos base
  - [x] 2.1 Configurar SQLAlchemy com suporte async
    - Criar db/engine.py com async engine e session factory
    - Criar db/base.py com Base declarativa
    - Implementar get_db() dependency para FastAPI
    - Configurar connection pooling
    - _Requisitos: 1.1, 2.1_
  
  - [x] 2.1.5 Configurar Alembic Assíncrono
    - Configurar Alembic para rodar com asyncpg (SQLAlchemy assíncrono)
    - Configurar env.py gerado pelo Alembic para usar context.configure(connection=connection, target_metadata=Base.metadata) dentro de um bloco asyncio.run()
    - _Requisitos: 1.1, 2.1_
  
  - [x] 2.2 Criar modelo Tenant com isolamento
    - Criar db/models/tenant.py com campos: id, name, slug, settings, created_at
    - Adicionar índices únicos em slug
    - Criar migration inicial com Alembic
    - _Requisitos: 1.1, 1.2_
  
  - [x] 2.3 Criar modelos de usuário e autenticação
    - Criar db/models/user.py com tenant_id, email, hashed_password, role
    - Adicionar enum UserRole (admin, lawyer, assistant)
    - Criar índices compostos (tenant_id, email)
    - _Requisitos: 1.3, 1.4_
  
  - [x] 2.4 Criar modelos do CRM (Leads e Clients)
    - Criar db/models/lead.py com tenant_id, status, source, score, metadata
    - Criar db/models/client.py com tenant_id, lead_id, status, health_score
    - Adicionar enums: LeadStatus, ClientStatus
    - Criar índices para queries frequentes
    - _Requisitos: 2.1, 2.2, 2.3, 3.1, 3.2_
  
  - [x] 2.5 Criar modelos de processos jurídicos
    - Criar db/models/legal_case.py com tenant_id, client_id, case_number, court
    - Criar db/models/case_movement.py com case_id, date, type, content, embedding
    - Adicionar suporte pgvector para embeddings (vector(1536))
    - Criar índices GIN para busca full-text
    - _Requisitos: 2.4, 2.5, 2.6_


  - [x] 2.6 Criar modelos de IA e configuração
    - Criar db/models/ai_provider.py com name, model, priority, rate_limit
    - Criar db/models/ai_conversation.py com tenant_id, client_id, messages
    - Criar db/models/briefing.py com tenant_id, date, content, metadata
    - _Requisitos: 2.7, 2.8_
  
  - [x] 2.7 Criar modelos de eventos e automações
    - Criar db/models/event.py com tenant_id, type, entity_id, payload
    - Criar db/models/automation.py com tenant_id, trigger, actions, enabled
    - Adicionar índices para queries de eventos por tipo e data
    - _Requisitos: 3.3, 3.4_
  
  - [ ]* 2.8 Escrever testes de propriedade para modelos
    - Testar integridade referencial entre modelos
    - Testar constraints de tenant_id em todas as tabelas
    - Testar unicidade de índices compostos
    - _Requisitos: 1.1, 1.2_

- [x] 3. Implementar sistema multi-tenant e middleware
  - [x] 3.1 Criar middleware de isolamento de tenant
    - Criar core/middleware/tenant.py com TenantMiddleware
    - Extrair tenant_id de header X-Tenant-ID ou JWT
    - Injetar tenant_id no contexto da request
    - Retornar 403 se tenant inválido
    - _Requisitos: 1.1, 1.2_
  
  - [x] 3.2 Implementar Repository pattern com tenant filtering
    - Criar core/repositories/base.py com BaseRepository
    - Adicionar métodos: get(), list(), create(), update(), delete()
    - Aplicar filtro automático por tenant_id em todas as queries
    - Implementar soft delete opcional
    - _Requisitos: 1.1, 1.2_
  
  - [x] 3.3 Criar repositories específicos
    - Criar repositories/tenant.py, user.py, lead.py, client.py
    - Criar repositories/legal_case.py, case_movement.py
    - Adicionar métodos específicos de negócio (ex: get_active_leads)
    - _Requisitos: 2.1, 2.2, 2.3, 2.4_
  
  - [ ]* 3.4 Escrever testes de isolamento multi-tenant
    - Testar que queries não vazam dados entre tenants
    - Testar que middleware bloqueia acessos inválidos
    - Testar soft delete por tenant
    - _Requisitos: 1.1, 1.2_

- [x] 4. Implementar autenticação e autorização
  - [x] 4.1 Criar sistema de JWT com RBAC
    - Criar core/auth/jwt.py com create_token(), verify_token()
    - Adicionar claims: user_id, tenant_id, role, permissions
    - Configurar expiração e refresh tokens
    - _Requisitos: 1.3, 1.4_
  
  - [x] 4.2 Criar dependencies de autorização
    - Criar core/auth/dependencies.py com get_current_user()
    - Criar require_role() e require_permission() decorators
    - Implementar verificação de tenant_id do token vs recurso
    - _Requisitos: 1.3, 1.4_
  
  - [x] 4.3 Implementar endpoints de autenticação
    - Criar api/routes/auth.py com /login, /refresh, /logout
    - Adicionar validação de credenciais com bcrypt
    - Implementar rate limiting em /login (5 tentativas/min)
    - _Requisitos: 1.3_
  
  - [ ]* 4.4 Escrever testes de segurança
    - Testar que tokens expirados são rejeitados
    - Testar que usuários não acessam recursos de outros tenants
    - Testar rate limiting de login
    - _Requisitos: 1.3, 1.4_

- [x] 5. Configurar sistema de jobs assíncronos (Taskiq)
  - [x] 5.1 Configurar Taskiq com Redis broker
    - Criar workers/broker.py com configuração do broker
    - Configurar serialização JSON e retry policy
    - Adicionar middleware de logging
    - Criar workers/main.py como entry point
    - Acoplar o broker ao Lifespan do FastAPI em api/main.py para inicializar e desligar o pool do Redis graciosamente junto com o servidor web
    - _Requisitos: 2.5, 2.6, 2.7_


  - [x] 5.2 Criar sistema de event bus
    - Criar workers/events/bus.py com publish() e subscribe()
    - Definir event types em workers/events/types.py
    - Implementar garantias de entrega (at-least-once)
    - Adicionar dead letter queue para falhas
    - _Requisitos: 3.3, 3.4_
  
  - [x] 5.3 Implementar workers base
    - Criar workers/tasks/base.py com BaseTask
    - Adicionar decorators para retry e timeout
    - Implementar logging estruturado
    - Configurar concorrência e rate limiting
    - _Requisitos: 2.5, 2.6, 2.7_
  
  - [ ]* 5.4 Escrever testes de workers
    - Testar retry em caso de falha
    - Testar dead letter queue
    - Testar rate limiting de tasks
    - _Requisitos: 2.5, 2.6_

- [x] 6. Implementar integração com Chatwit
  - [x] 6.1 Criar webhook endpoint para Chatwit
    - Criar api/routes/webhooks/chatwit.py com POST /webhooks/chatwit
    - Validar assinatura HMAC do webhook
    - Parsear eventos: message_received, tag_added, tag_removed
    - Publicar eventos no event bus
    - _Requisitos: 2.1_
  
  - [x] 6.2 Criar API client do Chatwit
    - Criar services/chatwit/client.py com send_message(), add_tag()
    - Implementar rate limiting (100 req/min)
    - Adicionar retry exponencial
    - Configurar timeout de 30s
    - _Requisitos: 2.1_
  
  - [x] 6.3 Implementar event handlers do Chatwit
    - Criar workers/tasks/chatwit_handlers.py
    - Handler para message_received: criar/atualizar lead
    - Handler para tag_added: atualizar status do lead
    - Handler para tag_removed: remover automações
    - _Requisitos: 2.1, 2.2_
  
  - [x] 6.4 Implementar sistema de tags ativas
    - Criar services/chatwit/tags.py com get_active_tags()
    - Sincronizar tags do Chatwit com banco local
    - Mapear tags para estados do funil
    - _Requisitos: 2.1, 2.2_
  
  - [ ]* 6.5 Escrever testes de integração Chatwit
    - Testar validação de assinatura HMAC
    - Testar parsing de eventos
    - Testar rate limiting do client
    - _Requisitos: 2.1_

- [x] 7. Implementar integração com DataJud
  - [x] 7.1 Criar API client do DataJud
    - Criar services/datajud/client.py com search_cases(), get_movements()
    - Implementar autenticação com certificado digital
    - Adicionar rate limiting (1 req/36s = 100 req/hora)
    - Implementar retry com backoff exponencial
    - _Requisitos: 2.4, 2.5_
  
  - [x] 7.2 Implementar sistema de batching
    - Criar services/datajud/batcher.py
    - Agrupar processos em lotes de 100
    - Distribuir lotes ao longo de 6 horas
    - Calcular delays entre requisições (36s)
    - _Requisitos: 2.5_
  
  - [x] 7.3 Criar parser de movimentações com round-trip
    - Criar services/datajud/parser.py
    - Parsear XML/JSON de movimentações
    - Normalizar datas, tipos, conteúdo
    - Validar round-trip (parse -> serialize -> parse)
    - _Requisitos: 2.5, 2.6_


  - [x] 7.4 Implementar worker de polling do DataJud
    - Criar workers/tasks/datajud_poller.py
    - Buscar processos ativos por tenant
    - Agendar consultas respeitando rate limit
    - Processar movimentações novas
    - Publicar eventos de atualização
    - _Requisitos: 2.4, 2.5, 2.6_
  
  - [ ]* 7.5 Escrever testes de integração DataJud
    - Testar rate limiting (1 req/36s)
    - Testar batching de 100 processos
    - Testar round-trip do parser
    - _Requisitos: 2.4, 2.5_

- [x] 8. Checkpoint - Validar integrações base
  - Executar testes de integração Chatwit e DataJud
  - Verificar rate limiting funcionando
  - Testar event bus com eventos reais
  - Perguntar ao usuário se há dúvidas ou ajustes necessários

- [x] 9. Implementar sistema de IA com LangGraph
  - [x] 9.1 Configurar LiteLLM com roteamento dinâmico
    - Criar services/ai/litellm_config.py
    - Configurar fallback: OpenAI -> Anthropic -> Groq
    - Implementar rate limiting por provider
    - Adicionar retry e circuit breaker
    - _Requisitos: 2.7_
  
  - [x] 9.2 Criar sistema de providers dinâmicos
    - Criar services/ai/provider_manager.py
    - Carregar configuração de ai_providers do banco
    - Implementar seleção por prioridade e disponibilidade
    - Atualizar rate limits em tempo real
    - _Requisitos: 2.7_
  
  - [x] 9.3 Implementar Agente de Triagem
    - Criar services/ai/agents/triage.py
    - Analisar mensagem do lead
    - Classificar urgência (alta, média, baixa)
    - Extrair entidades (nome, telefone, tipo de caso)
    - Calcular score inicial do lead
    - _Requisitos: 2.2, 2.7_
  
  - [x] 9.4 Implementar Agente Investigador
    - Criar services/ai/agents/investigator.py
    - Buscar movimentações relacionadas ao caso
    - Usar busca semântica com embeddings
    - Identificar padrões e anomalias
    - Gerar insights sobre o processo
    - _Requisitos: 2.6, 2.7_
  
  - [x] 9.5 Implementar Agente Redator
    - Criar services/ai/agents/writer.py
    - Gerar resumos de movimentações
    - Criar briefings personalizados
    - Traduzir juridiquês para linguagem simples
    - Adaptar tom para o público (cliente vs advogado)
    - _Requisitos: 2.8, 2.9_
  
  - [x] 9.6 Implementar Agente Maestro (orquestrador)
    - Criar services/ai/agents/maestro.py com LangGraph
    - Definir grafo de estados: Triagem -> Investigação -> Redação
    - Implementar roteamento condicional
    - Adicionar loops de refinamento
    - Gerenciar contexto entre agentes
    - _Requisitos: 2.7, 2.8_
  
  - [x] 9.7 Implementar fluxo Briefing Matinal
    - Criar services/ai/workflows/morning_briefing.py
    - Buscar movimentações das últimas 24h
    - Classificar por urgência (Urgente, Atenção, Boas Notícias, Ruído)
    - Gerar resumo executivo por cliente
    - Salvar briefing no banco
    - _Requisitos: 2.8, 4.1_
  
  - [x] 9.8 Implementar Tradutor Juridiquês
    - Criar services/ai/workflows/legal_translator.py
    - Receber texto jurídico complexo
    - Simplificar linguagem mantendo precisão
    - Adicionar explicações de termos técnicos
    - Retornar versão acessível
    - _Requisitos: 2.9_


  - [ ]* 9.9 Escrever testes de agentes de IA
    - Testar fallback entre providers
    - Testar classificação de urgência do Agente Triagem
    - Testar busca semântica do Agente Investigador
    - Testar qualidade de resumos do Agente Redator
    - _Requisitos: 2.7, 2.8, 2.9_

- [x] 10. Implementar sistema de embeddings assíncrono
  - [x] 10.1 Criar worker de geração de embeddings
    - Criar workers/tasks/embeddings.py
    - Processar movimentações em lote (batch de 50)
    - Gerar embeddings com OpenAI text-embedding-3-small
    - Salvar vetores no campo embedding (pgvector)
    - Implementar retry em caso de falha
    - _Requisitos: 2.6_
  
  - [x] 10.2 Implementar busca semântica
    - Criar services/search/semantic.py
    - Implementar similarity search com pgvector (<=>)
    - Adicionar filtros por tenant_id, case_id, date_range
    - Retornar top-k resultados com score
    - _Requisitos: 2.6_
  
  - [x] 10.3 Criar índice HNSW para performance
    - Adicionar migration com CREATE INDEX USING hnsw
    - Configurar parâmetros: m=16, ef_construction=64
    - Testar performance com 10k+ vetores
    - _Requisitos: 2.6_
  
  - [ ]* 10.4 Escrever testes de busca semântica
    - Testar que queries similares retornam resultados relevantes
    - Testar filtros por tenant
    - Testar performance com dataset grande
    - _Requisitos: 2.6_

- [x] 11. Implementar CRM - Funil Inteligente
  - [x] 11.1 Criar API CRUD de leads
    - Criar api/routes/leads.py com GET, POST, PUT, DELETE
    - Adicionar filtros: status, source, score_min, date_range
    - Implementar paginação e ordenação
    - Validar schemas com Pydantic
    - _Requisitos: 2.1, 2.2_
  
  - [x] 11.2 Implementar transições de estado do lead arrasta e solta
    - Criar services/crm/lead_state_machine.py
    - Definir transições válidas: novo -> qualificado -> convertido
    - Validar transições e registrar histórico
    - Publicar eventos de mudança de estado
    - _Requisitos: 2.2_
  
  - [x] 11.3 Implementar score de leads com IA
    - Criar services/crm/lead_scorer.py
    - Analisar: urgência, tipo de caso, histórico de interações
    - Calcular score 0-100
    - Atualizar score automaticamente em eventos
    - _Requisitos: 2.2, 2.7_
  
  - [x] 11.4 Criar automações de funil
    - Criar services/crm/funnel_automations.py
    - Auto-qualificar leads com score > 70
    - Enviar mensagem de boas-vindas via Chatwit
    - Agendar follow-up automático
    - _Requisitos: 2.2, 3.3_
  
  - [ ]* 11.5 Escrever testes do funil
    - Testar transições de estado válidas e inválidas
    - Testar cálculo de score
    - Testar automações disparadas corretamente
    - _Requisitos: 2.2_

- [x] 12. Implementar CRM - Prontuário 360º
  - [x] 12.1 Criar API de clientes
    - Criar api/routes/clients.py com GET, POST, PUT
    - Endpoint GET /clients/:id/timeline para eventos
    - Endpoint GET /clients/:id/health para painel de saúde
    - Endpoint POST /clients/:id/notes para notas internas
    - _Requisitos: 3.1, 3.2, 3.3_


  - [x] 12.2 Implementar timeline de eventos
    - Criar services/crm/timeline.py
    - Agregar eventos: movimentações, mensagens, notas, automações
    - Ordenar cronologicamente
    - Adicionar filtros por tipo e período
    - Implementar paginação infinita
    - _Requisitos: 3.2_
  
  - [x] 12.3 Implementar painel de saúde do cliente
    - Criar services/crm/health_dashboard.py
    - Calcular health_score baseado em: atividade, satisfação, risco
    - Identificar alertas: processos parados, prazos próximos
    - Gerar recomendações de ação
    - _Requisitos: 3.2_
  
  - [x] 12.4 Implementar sistema de automações individuais
    - Criar db/models/client_automation.py com toggles por cliente
    - Tipos: briefing_matinal, alertas_urgentes, resumo_semanal
    - Endpoint PUT /clients/:id/automations para configurar
    - Respeitar configurações ao disparar automações
    - _Requisitos: 3.3_
  
  - [x] 12.5 Implementar notas internas
    - Criar db/models/client_note.py com tenant_id, client_id, author_id
    - Suporte a markdown e menções (@user)
    - Endpoint para criar, editar, deletar notas
    - Notificar usuários mencionados
    - _Requisitos: 3.3_
  
  - [ ]* 12.6 Escrever testes do prontuário
    - Testar agregação de timeline
    - Testar cálculo de health_score
    - Testar toggles de automações
    - _Requisitos: 3.1, 3.2, 3.3_

- [x] 13. Implementar CRM - Central Operacional
  - [x] 13.1 Criar API do dashboard
    - Criar api/routes/dashboard.py
    - Endpoint GET /dashboard/urgent para casos urgentes
    - Endpoint GET /dashboard/attention para casos que precisam atenção
    - Endpoint GET /dashboard/good-news para boas notícias
    - Endpoint GET /dashboard/noise para ruído
    - Endpoint GET /dashboard/metrics para indicadores
    - _Requisitos: 4.1, 4.2, 4.3_
  
  - [x] 13.2 Implementar agregação de dados do briefing
    - Criar services/dashboard/aggregator.py
    - Buscar briefings do dia por tenant
    - Classificar movimentações nos 4 blocos
    - Calcular métricas: total de casos, novos hoje, pendentes
    - Cachear resultados por 5 minutos
    - _Requisitos: 4.1_
  
  - [x] 13.3 Implementar métricas do escritório
    - Criar services/dashboard/metrics.py
    - Calcular: taxa de conversão, tempo médio de resposta, satisfação
    - Comparar com período anterior (variação %)
    - Gerar gráficos de tendência
    - _Requisitos: 4.2_
  
  - [x] 13.4 Implementar filtros e personalização
    - Adicionar filtros: período, advogado, tipo de caso
    - Salvar preferências de visualização por usuário
    - Implementar refresh automático (WebSocket)
    - _Requisitos: 4.1, 4.2_
  
  - [ ]* 13.5 Escrever testes do dashboard
    - Testar agregação dos 4 blocos
    - Testar cálculo de métricas
    - Testar cache de resultados
    - _Requisitos: 4.1, 4.2_

- [x] 14. Checkpoint - Validar backend completo
  - Executar todos os testes unitários e de integração
  - Testar fluxo completo: webhook Chatwit -> lead -> cliente -> briefing
  - Verificar performance de queries com dados de teste
  - Perguntar ao usuário se há ajustes necessários antes do frontend


- [x] 15. Configurar frontend Next.js 16
  - [x] 15.1 Criar estrutura base do App Router
    - Criar app/layout.tsx com providers
    - Criar app/page.tsx como landing page
    - Configurar app/(auth)/login/page.tsx
    - Criar app/(dashboard)/layout.tsx com sidebar
    - _Requisitos: 4.1, 4.2, 4.3_
  
  - [x] 15.2 Configurar Shadcn/UI e componentes base
    - Instalar componentes: button, card, dialog, table, form
    - Criar components/ui/ com componentes customizados
    - Configurar tema dark/light
    - Criar components/layout/Sidebar.tsx
    - _Requisitos: 4.1, 4.2, 4.3_
  
  - [x] 15.3 Configurar autenticação no frontend
    - Criar lib/auth.ts com funções de login/logout
    - Implementar middleware.ts para proteção de rotas
    - Criar hooks/useAuth.ts com contexto de usuário
    - Salvar token em httpOnly cookie
    - _Requisitos: 1.3_
  
  - [x] 15.4 Configurar API client com React Query
    - Criar lib/api-client.ts com axios configurado
    - Adicionar interceptors para token e tenant_id
    - Configurar React Query com cache e refetch
    - Criar hooks/api/ para cada recurso
    - _Requisitos: Todos (comunicação com backend)_
  
  - [ ]* 15.5 Escrever testes do setup base
    - Testar proteção de rotas
    - Testar refresh de token
    - Testar interceptors do API client
    - _Requisitos: 1.3_

- [x] 16. Implementar página Dashboard (Central Operacional)
  - [x] 16.1 Criar layout do dashboard
    - Criar app/(dashboard)/page.tsx
    - Implementar grid responsivo com 5 blocos
    - Adicionar filtros de período e advogado
    - Implementar skeleton loading
    - _Requisitos: 4.1, 4.2_
  
  - [x] 16.2 Criar componente de casos urgentes
    - Criar components/dashboard/UrgentCases.tsx
    - Listar casos com prazo < 3 dias
    - Adicionar badge de urgência
    - Link para prontuário do cliente
    - _Requisitos: 4.1_
  
  - [x] 16.3 Criar componente de casos que precisam atenção
    - Criar components/dashboard/AttentionCases.tsx
    - Listar casos parados > 30 dias
    - Mostrar última movimentação
    - Botão de ação rápida
    - _Requisitos: 4.1_
  
  - [x] 16.4 Criar componente de boas notícias
    - Criar components/dashboard/GoodNews.tsx
    - Listar decisões favoráveis
    - Mostrar resumo gerado por IA
    - Botão para compartilhar com cliente
    - _Requisitos: 4.1_
  
  - [x] 16.5 Criar componente de ruído
    - Criar components/dashboard/Noise.tsx
    - Listar movimentações irrelevantes
    - Opção de marcar como lida
    - Filtro para ocultar
    - _Requisitos: 4.1_
  
  - [x] 16.6 Criar componente de métricas
    - Criar components/dashboard/Metrics.tsx
    - Mostrar KPIs: conversão, tempo resposta, satisfação
    - Gráficos com recharts
    - Comparação com período anterior
    - _Requisitos: 4.2_
  
  - [x] 16.7 Implementar atualização em tempo real
    - Configurar WebSocket ou SSE
    - Atualizar dashboard automaticamente
    - Mostrar notificação de novos eventos
    - _Requisitos: 4.1_


  - [ ]* 16.8 Escrever testes E2E do dashboard
    - Testar carregamento de todos os blocos
    - Testar filtros funcionando
    - Testar atualização em tempo real
    - _Requisitos: 4.1, 4.2_

- [x] 17. Implementar página Funil Kanban
  - [x] 17.1 Criar layout do funil
    - Criar app/(dashboard)/funil/page.tsx
    - Implementar board Kanban com colunas: Novo, Qualificado, Convertido
    - Adicionar filtros e busca
    - Implementar drag-and-drop com dnd-kit
    - _Requisitos: 2.1, 2.2_
  
  - [x] 17.2 Criar componente de card de lead
    - Criar components/funil/LeadCard.tsx
    - Mostrar: nome, score, fonte, última interação
    - Badge de urgência
    - Menu de ações rápidas
    - _Requisitos: 2.1, 2.2_
  
  - [x] 17.3 Implementar drag-and-drop de leads
    - Configurar dnd-kit para mover entre colunas
    - Validar transições de estado
    - Atualizar backend via API
    - Otimistic updates
    - _Requisitos: 2.2_
  
  - [x] 17.4 Criar modal de detalhes do lead
    - Criar components/funil/LeadDetailsModal.tsx
    - Mostrar histórico de interações
    - Formulário de edição
    - Botão de conversão para cliente
    - _Requisitos: 2.1, 2.2_
  
  - [x] 17.5 Implementar filtros e busca
    - Filtrar por: fonte, score, período
    - Busca por nome, telefone, email
    - Salvar filtros aplicados
    - _Requisitos: 2.1_
  
  - [ ]* 17.6 Escrever testes E2E do funil
    - Testar drag-and-drop funcionando
    - Testar validação de transições
    - Testar conversão de lead para cliente
    - _Requisitos: 2.2_

- [x] 18. Implementar página Prontuário 360º
  - [x] 18.1 Criar layout do prontuário
    - Criar app/(dashboard)/clientes/[id]/page.tsx
    - Implementar layout com sidebar de navegação
    - Seções: Visão Geral, Timeline, Processos, Automações, Notas
    - _Requisitos: 3.1, 3.2, 3.3_
  
  - [x] 18.2 Criar seção Visão Geral
    - Criar components/prontuario/Overview.tsx
    - Mostrar dados do cliente e health score
    - Cards com métricas: processos ativos, últimas interações
    - Alertas e recomendações
    - _Requisitos: 3.1, 3.2_
  
  - [x] 18.3 Criar seção Timeline
    - Criar components/prontuario/Timeline.tsx
    - Listar eventos cronologicamente
    - Filtros por tipo de evento
    - Infinite scroll
    - _Requisitos: 3.2_
  
  - [x] 18.4 Criar seção Processos
    - Criar components/prontuario/Cases.tsx
    - Listar processos do cliente
    - Mostrar status e última movimentação
    - Link para detalhes do processo
    - _Requisitos: 3.1_
  
  - [x] 18.5 Criar seção Automações
    - Criar components/prontuario/Automations.tsx
    - Toggles para: briefing matinal, alertas urgentes, resumo semanal
    - Salvar configurações via API
    - Mostrar histórico de automações disparadas
    - _Requisitos: 3.3_


  - [x] 18.6 Criar seção Notas Internas
    - Criar components/prontuario/Notes.tsx
    - Editor markdown com preview
    - Sistema de menções @user
    - Listar notas com autor e data
    - _Requisitos: 3.3_
  
  - [ ]* 18.7 Escrever testes E2E do prontuário
    - Testar navegação entre seções
    - Testar toggles de automações
    - Testar criação de notas
    - _Requisitos: 3.1, 3.2, 3.3_

- [x] 19. Implementar sistema de notificações
  - [x] 19.1 Criar componente de notificações
    - Criar components/notifications/NotificationCenter.tsx
    - Badge com contador de não lidas
    - Dropdown com lista de notificações
    - Marcar como lida
    - _Requisitos: 3.4_
  
  - [x] 19.2 Implementar WebSocket para notificações
    - Criar lib/websocket.ts com conexão persistente
    - Receber eventos do backend
    - Atualizar UI em tempo real
    - Reconectar automaticamente
    - Implementar autenticação via ticket/token de curta duração ou extrair JWT via query parameter (ex: ?token=xyz) com validação estrita no backend
    - _Requisitos: 3.4_
  
  - [x] 19.3 Criar tipos de notificações
    - Nova movimentação urgente
    - Lead qualificado automaticamente
    - Briefing matinal disponível
    - Menção em nota
    - _Requisitos: 3.4_
  
  - [ ]* 19.4 Escrever testes de notificações
    - Testar recebimento via WebSocket
    - Testar marcar como lida
    - Testar reconexão automática
    - _Requisitos: 3.4_

- [x] 20. Implementar observabilidade e monitoramento
  - [x] 20.1 Configurar logging estruturado
    - Criar core/logging.py com structlog
    - Adicionar contexto: tenant_id, user_id, request_id
    - Configurar níveis: DEBUG, INFO, WARNING, ERROR
    - Enviar logs para stdout (Docker)
    - _Requisitos: Todos (observabilidade)_
  
  - [x] 20.2 Implementar métricas Prometheus
    - Criar core/metrics.py com prometheus_client
    - Métricas: request_duration, request_count, error_rate
    - Métricas de negócio: leads_created, cases_updated
    - Endpoint /metrics para scraping
    - _Requisitos: Todos (observabilidade)_
  
  - [x] 20.3 Criar health checks
    - Criar api/routes/health.py
    - Endpoint GET /health/live (liveness)
    - Endpoint GET /health/ready (readiness)
    - Verificar: database, redis, external APIs
    - _Requisitos: Todos (observabilidade)_
  
  - [x] 20.4 Implementar audit logs
    - Criar db/models/audit_log.py
    - Registrar: ações de usuários, mudanças de estado, acessos
    - Middleware para capturar automaticamente
    - Endpoint para consultar logs
    - _Requisitos: 1.4_
  
  - [ ]* 20.5 Escrever testes de observabilidade
    - Testar que logs contêm contexto correto
    - Testar que métricas são incrementadas
    - Testar health checks
    - _Requisitos: Todos_

- [x] 21. Implementar seeds e dados de teste
  - [x] 21.1 Criar seed de tenant demo
    - Criar db/seeds/tenant.py
    - Criar tenant "Demo Law Firm" com configurações
    - Criar usuários: admin, advogado, assistente
    - _Requisitos: 1.1, 1.3_


  - [x] 21.2 Criar seed de leads e clientes
    - Criar db/seeds/crm.py
    - Criar 20 leads em diferentes estados
    - Criar 10 clientes com processos
    - Gerar interações e notas
    - _Requisitos: 2.1, 2.2, 3.1_
  
  - [x] 21.3 Criar seed de processos e movimentações
    - Criar db/seeds/legal_cases.py
    - Criar 15 processos com números reais (fake)
    - Criar 100+ movimentações variadas
    - Gerar embeddings para busca semântica
    - _Requisitos: 2.4, 2.5, 2.6_
  
  - [x] 21.4 Criar seed de configurações de IA
    - Criar db/seeds/ai_config.py
    - Configurar providers: OpenAI, Anthropic, Groq
    - Definir prioridades e rate limits
    - _Requisitos: 2.7_
  
  - [x] 21.5 Criar comando de seed
    - Criar cli/seed.py com Click
    - Comando: python -m cli.seed --all
    - Opções: --tenant, --crm, --cases, --ai
    - Limpar dados antes de seed (--reset)
    - _Requisitos: Todos (desenvolvimento)_

- [x] 22. Criar documentação e scripts de desenvolvimento
  - [x] 22.1 Criar README.md do projeto
    - Documentar arquitetura e stack
    - Instruções de setup local
    - Comandos úteis (seed, migrate, test)
    - Estrutura de diretórios
    - _Requisitos: Todos (documentação)_
  
  - [x] 22.2 Criar scripts de desenvolvimento
    - Criar scripts/dev.sh para iniciar ambiente
    - Criar scripts/test.sh para rodar testes
    - Criar scripts/migrate.sh para migrations
    - Criar scripts/seed.sh para popular dados
    - _Requisitos: Todos (desenvolvimento)_
  
  - [x] 22.3 Criar documentação de API
    - Configurar OpenAPI/Swagger no FastAPI
    - Documentar todos os endpoints
    - Adicionar exemplos de request/response
    - Endpoint /docs para visualização
    - _Requisitos: Todos (documentação)_
  
  - [x] 22.4 Criar guia de contribuição
    - Criar CONTRIBUTING.md
    - Padrões de código e commits
    - Processo de PR e review
    - Como rodar testes
    - _Requisitos: Todos (documentação)_

- [x] 23. Implementar testes de integração E2E
  - [x] 23.1 Configurar Playwright
    - Instalar Playwright no frontend
    - Configurar playwright.config.ts
    - Criar fixtures para autenticação
    - _Requisitos: Todos (testes)_
  
  - [x] 23.2 Criar testes E2E do fluxo principal
    - Testar: Login -> Dashboard -> Ver caso urgente
    - Testar: Funil -> Mover lead -> Converter para cliente
    - Testar: Prontuário -> Ativar automação -> Ver timeline
    - _Requisitos: 2.2, 3.3, 4.1_
  
  - [x] 23.3 Criar testes E2E de integrações
    - Testar: Webhook Chatwit -> Lead criado -> Aparece no funil
    - Testar: DataJud polling -> Movimentação -> Notificação
    - Testar: Briefing matinal -> Dashboard atualizado
    - _Requisitos: 2.1, 2.5, 2.8_
  
  - [ ]* 23.4 Criar testes de performance
    - Testar tempo de carregamento do dashboard
    - Testar busca semântica com 10k+ vetores
    - Testar rate limiting das APIs
    - _Requisitos: Todos (performance)_


- [ ] 24. Otimizações e refinamentos finais
  - [x] 24.1 Otimizar queries do banco
    - Adicionar índices faltantes baseado em slow queries
    - Implementar eager loading para relacionamentos
    - Adicionar cache Redis para queries frequentes
    - _Requisitos: Todos (performance)_
  
  - [x] 24.2 Implementar rate limiting global
    - Criar middleware de rate limiting
    - Limites por endpoint: 100 req/min (geral), 10 req/min (IA)
    - Usar Redis para contadores
    - Retornar 429 com Retry-After header
    - _Requisitos: 1.4, 2.7_
  
  - [x] 24.3 Adicionar compressão e cache HTTP
    - Configurar gzip no FastAPI
    - Adicionar headers Cache-Control
    - Implementar ETags para recursos estáticos
    - _Requisitos: Todos (performance)_
  
  - [x] 24.4 Implementar graceful shutdown
    - Capturar SIGTERM no backend
    - Finalizar workers Taskiq gracefully
    - Fechar conexões do banco
    - Aguardar requests em andamento
    - _Requisitos: Todos (produção)_
  
  - [x] 24.5 Adicionar validações de segurança
    - Implementar CORS restritivo
    - Adicionar headers de segurança (CSP, HSTS)
    - Validar tamanho de payloads
    - Sanitizar inputs contra XSS/SQL injection
    - _Requisitos: 1.4_
  
  - [ ]* 24.6 Escrever testes de segurança
    - Testar CORS funcionando
    - Testar rate limiting
    - Testar validação de payloads grandes
    - _Requisitos: 1.4_

- [x] 25. Checkpoint final - Validação completa do sistema
  - Executar todos os testes (unit, integration, E2E)
  - Testar fluxo completo com dados de seed
  - Verificar performance e métricas
  - Validar documentação e scripts
  - Perguntar ao usuário se o sistema está pronto para deploy

## Notas

- Tarefas marcadas com `*` são opcionais e podem ser puladas para MVP mais rápido
- Cada tarefa referencia requisitos específicos para rastreabilidade
- Checkpoints garantem validação incremental
- Testes de propriedade validam invariantes universais
- Testes unitários validam casos específicos e edge cases
- Testes E2E validam fluxos completos de usuário

## Ordem de Execução Recomendada

1. Infraestrutura e modelos (tarefas 1-2)
2. Multi-tenancy e autenticação (tarefas 3-4)
3. Sistema de jobs e integrações (tarefas 5-7)
4. Sistema de IA (tarefas 9-10)
5. CRM backend (tarefas 11-13)
6. Frontend (tarefas 15-19)
7. Observabilidade e seeds (tarefas 20-21)
8. Documentação e testes finais (tarefas 22-24)

## Dependências Críticas

- Tarefa 2 depende de 1 (infraestrutura antes de modelos)
- Tarefa 3 depende de 2 (modelos antes de repositories)
- Tarefas 6-7 dependem de 5 (Taskiq antes de integrações)
- Tarefa 9 depende de 2 e 5 (modelos e jobs antes de IA)
- Tarefas 11-13 dependem de 2-4 (CRM depende de base de dados e auth)
- Tarefas 15-19 dependem de 11-13 (frontend depende de APIs backend)