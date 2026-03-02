# Sistema de IA com LangGraph - JusMonitorIA

Sistema completo de inteligência artificial para automação jurídica usando LangGraph, LiteLLM e múltiplos provedores de IA.

## Visão Geral

O sistema implementa 4 agentes especializados coordenados por um orquestrador (Maestro) usando LangGraph:

1. **Agente de Triagem** - Qualificação de leads
2. **Agente Investigador** - Análise de processos
3. **Agente Redator** - Geração de documentos
4. **Agente Maestro** - Orquestração com LangGraph

## Arquitetura

```
app/ai/
├── agents/
│   ├── base_agent.py       # Classe base para todos os agentes
│   ├── triage.py           # Agente de Triagem
│   ├── investigator.py     # Agente Investigador
│   ├── writer.py           # Agente Redator
│   └── maestro.py          # Agente Maestro (LangGraph)
├── providers/
│   ├── litellm_config.py   # Configuração LiteLLM com fallback
│   └── provider_manager.py # Gerenciamento dinâmico de providers
└── workflows/
    ├── morning_briefing.py # Workflow de briefing matinal
    └── legal_translator.py # Tradutor de juridiquês
```

## Funcionalidades Implementadas

### 1. LiteLLM com Roteamento Dinâmico (Task 9.1)

**Arquivo:** `providers/litellm_config.py`

- ✅ Configuração de fallback: OpenAI -> Gemini (Google) -> Anthropic
- ✅ Rate limiting por provider (token bucket)
- ✅ Retry com backoff exponencial (1s, 2s, 4s)
- ✅ Circuit breaker pattern (5 falhas = 60s timeout)
- ✅ Suporte a embeddings (text-embedding-3-small)

**Uso:**
```python
from app.ai.providers.litellm_config import litellm_config

# Chamar LLM com fallback automático
response = await litellm_config.call_with_fallback(
    messages=[
        {"role": "system", "content": "Você é um assistente jurídico"},
        {"role": "user", "content": "Analise este caso..."}
    ],
    temperature=0.7,
)

# Gerar embedding
embedding = await litellm_config.generate_embedding("texto para embedding")
```

### 2. Sistema de Providers Dinâmicos (Task 9.2)

**Arquivos:** 
- `providers/provider_manager.py`
- `db/repositories/ai_provider_repository.py`

- ✅ Carregamento de configuração do banco (ai_providers)
- ✅ Seleção por prioridade e disponibilidade
- ✅ Atualização de rate limits em tempo real
- ✅ Tracking de uso por provider
- ✅ Enable/disable providers dinamicamente

**Uso:**
```python
from app.ai.providers.provider_manager import ProviderManager

manager = ProviderManager(session, tenant_id)

# Chamar LLM com providers do banco
response = await manager.call_llm(
    messages=[...],
    temperature=0.7,
)

# Adicionar novo provider
provider = await manager.add_provider(
    provider="openai",
    model="gpt-4-turbo-preview",
    api_key="sk-...",
    priority=100,
)

# Atualizar prioridade
await manager.update_provider_priority(provider.id, new_priority=50)
```

### 3. Agente de Triagem (Task 9.3)

**Arquivo:** `agents/triage.py`

- ✅ Análise de mensagens de leads
- ✅ Classificação de urgência (baixa, média, alta, crítica)
- ✅ Extração de entidades (nome, telefone, email, CPF)
- ✅ Cálculo de score inicial (0-100)
- ✅ Recomendação de próxima ação

**Uso:**
```python
from app.ai.agents.triage import TriagemAgent

agent = TriagemAgent(session, tenant_id)

# Qualificar lead
result = await agent.qualify_lead(
    message="Preciso de um advogado urgente para um caso trabalhista...",
    contact_info={"phone": "+5511999999999"},
)

# Resultado:
# {
#     "nome": "João Silva",
#     "telefone": "+5511999999999",
#     "tipo_caso": "Trabalhista",
#     "area_direito": "Trabalhista",
#     "urgencia": "alta",
#     "resumo": "Cliente precisa de advogado para caso trabalhista urgente",
#     "proxima_acao": "agendar_consulta",
#     "score": 85,
#     "justificativa_score": "Alta urgência e caso bem definido"
# }
```

### 4. Agente Investigador (Task 9.4)

**Arquivo:** `agents/investigator.py`

- ✅ Busca de movimentações relacionadas
- ✅ Busca semântica com embeddings (preparado para pgvector)
- ✅ Identificação de padrões e anomalias
- ✅ Geração de insights sobre processos
- ✅ Detecção de prazos e deadlines

**Uso:**
```python
from app.ai.agents.investigator import InvestigadorAgent

agent = InvestigadorAgent(session, tenant_id)

# Analisar movimentações
result = await agent.analyze_movements(
    process_info={"cnj_number": "0001234-56.2023.8.26.0100"},
    movements=[
        {"date": "2024-01-15", "description": "Sentença proferida..."},
        {"date": "2024-01-10", "description": "Audiência realizada..."},
    ],
)

# Resultado:
# {
#     "resumo": "Processo com sentença recente...",
#     "movimentacoes_importantes": [...],
#     "prazos": [{"data": "2024-02-15", "descricao": "Prazo para recurso"}],
#     "requer_acao": True,
#     "proximos_passos": ["Avaliar recurso", "Notificar cliente"],
#     "padroes": {...}
# }
```

### 5. Agente Redator (Task 9.5)

**Arquivo:** `agents/writer.py`

- ✅ Geração de resumos de movimentações
- ✅ Criação de briefings personalizados
- ✅ Tradução de juridiquês para linguagem simples
- ✅ Adaptação de tom (cliente vs advogado vs executivo)
- ✅ Rascunho de documentos jurídicos

**Uso:**
```python
from app.ai.agents.writer import RedatorAgent

agent = RedatorAgent(session, tenant_id)

# Gerar resumo para cliente
summary = await agent.generate_movement_summary(
    movements=[...],
    audience="cliente",
    max_length=300,
)

# Criar briefing
briefing = await agent.create_briefing(
    client_name="João Silva",
    processes=[...],
    period="últimas 24 horas",
)

# Traduzir juridiquês
translated = await agent.translate_legal_jargon(
    legal_text="O réu foi citado e apresentou contestação...",
    add_explanations=True,
)
```

### 6. Agente Maestro com LangGraph (Task 9.6)

**Arquivo:** `agents/maestro.py`

- ✅ Grafo de estados com LangGraph
- ✅ Roteamento condicional entre agentes
- ✅ Loops de refinamento (máx 5 iterações)
- ✅ Gerenciamento de contexto entre agentes
- ✅ Consolidação de resultados

**Uso:**
```python
from app.ai.agents.maestro import MaestroAgent

maestro = MaestroAgent(session, tenant_id)

# Executar workflow completo
result = await maestro.execute_workflow(
    task_type="qualificar_lead",
    initial_message="Analisar este lead...",
    context={
        "message": "Preciso de advogado...",
        "contact": {...},
    },
)

# O Maestro decide automaticamente:
# 1. Qual agente usar (Triagem, Investigador, Redator)
# 2. Se precisa de múltiplos agentes
# 3. Quando o trabalho está completo
```

**Fluxo do LangGraph:**
```
START -> Maestro (decisão)
         ├─> Triagem -> Maestro
         ├─> Investigador -> Maestro
         ├─> Redator -> Maestro
         └─> END (quando completo)
```

### 7. Workflow Briefing Matinal (Task 9.7)

**Arquivo:** `workflows/morning_briefing.py`

- ✅ Busca movimentações das últimas 24h
- ✅ Classificação por urgência (Urgente, Atenção, Boas Notícias, Ruído)
- ✅ Geração de resumo executivo por cliente
- ✅ Preparado para salvar no banco

**Uso:**
```python
from app.ai.workflows.morning_briefing import MorningBriefingWorkflow

workflow = MorningBriefingWorkflow(session, tenant_id)

# Gerar briefing do dia
briefing = await workflow.generate_briefing(
    date_for=date.today(),
    hours_back=24,
)

# Resultado:
# {
#     "date": "2024-01-20",
#     "urgente": [...],
#     "atencao": [...],
#     "boas_noticias": [...],
#     "ruido": [...],
#     "summary": "Resumo executivo...",
#     "total_movements": 42
# }

# Briefing por cliente
client_briefing = await workflow.generate_client_briefing(
    client_id=client_uuid,
    hours_back=24,
)
```

### 8. Tradutor Juridiquês (Task 9.8)

**Arquivo:** `workflows/legal_translator.py`

- ✅ Tradução de texto jurídico complexo
- ✅ Simplificação mantendo precisão
- ✅ Explicações de termos técnicos
- ✅ Dicionário de 20+ termos comuns
- ✅ Cálculo de score de complexidade

**Uso:**
```python
from app.ai.workflows.legal_translator import LegalTranslator

translator = LegalTranslator(session, tenant_id)

# Traduzir texto
result = await translator.translate(
    legal_text="O réu foi citado e apresentou contestação tempestiva...",
    add_explanations=True,
)

# Resultado:
# {
#     "original": "O réu foi citado...",
#     "translated": "O acusado foi oficialmente informado (citação é a notificação formal)...",
#     "terms_explained": [
#         {"term": "citação", "explanation": "notificação oficial sobre o processo"},
#         {"term": "contestação", "explanation": "resposta do réu ao processo"}
#     ],
#     "complexity_score": 65,
#     "detected_terms": ["citação", "contestação"]
# }

# Explicar termo específico
explanation = await translator.explain_term("liminar")
# "decisão provisória urgente"
```

## Configuração de Providers

### Variáveis de Ambiente

```env
# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4-turbo-preview
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Google (Gemini)
GOOGLE_API_KEY=...
GOOGLE_MODEL=gemini-pro

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-3-opus-20240229

# LiteLLM
LITELLM_FALLBACK_ENABLED=true
LITELLM_RETRY_ATTEMPTS=3
LITELLM_TIMEOUT_SECONDS=60

# Rate Limiting
RATE_LIMIT_AI_PER_MINUTE=10
```

### Configuração no Banco de Dados

Os providers também podem ser configurados dinamicamente no banco:

```sql
INSERT INTO ai_providers (tenant_id, provider, model, api_key_encrypted, priority, is_active)
VALUES 
  ('tenant-uuid', 'openai', 'gpt-4-turbo-preview', 'encrypted-key', 100, true),
  ('tenant-uuid', 'google', 'gemini-pro', 'encrypted-key', 80, true),
  ('tenant-uuid', 'anthropic', 'claude-3-opus-20240229', 'encrypted-key', 60, true);
```

## Fallback Chain

O sistema implementa fallback automático na seguinte ordem:

1. **OpenAI** (prioridade 100)
   - Modelo: gpt-4-turbo-preview
   - Embeddings: text-embedding-3-small

2. **Gemini/Google** (prioridade 80)
   - Modelo: gemini-pro
   - Fallback se OpenAI falhar

3. **Anthropic** (prioridade 60)
   - Modelo: claude-3-opus-20240229
   - Último fallback

## Rate Limiting

### Circuit Breaker
- **Threshold:** 5 falhas consecutivas
- **Recovery:** 60 segundos
- **Comportamento:** Pula provider temporariamente

### Token Bucket
- **Rate:** 10 requisições/minuto (configurável)
- **Refill:** Contínuo baseado em tempo
- **Comportamento:** Aguarda ou tenta próximo provider

### Retry Logic
- **Tentativas:** 3 (configurável)
- **Backoff:** Exponencial (1s, 2s, 4s)
- **Erros:** RateLimitError, Timeout, APIConnectionError

## Requisitos Validados

- ✅ **Requirement 2.2** - Gestão de Leads (Agente Triagem)
- ✅ **Requirement 2.6** - Classificação de Movimentações (Agente Investigador)
- ✅ **Requirement 2.7** - Integração com LiteLLM (Todos os agentes)
- ✅ **Requirement 2.8** - Briefing Matinal (Workflow)
- ✅ **Requirement 2.9** - Tradutor Juridiquês (Workflow)
- ✅ **Requirement 4.1** - Dashboard (Briefing Matinal)

## Próximos Passos

1. **Implementar embeddings com pgvector**
   - Busca semântica de processos similares
   - Índice HNSW para performance

2. **Adicionar cache de respostas**
   - Redis para respostas frequentes
   - TTL configurável por tipo de query

3. **Implementar métricas**
   - Tempo de resposta por provider
   - Taxa de sucesso/falha
   - Custo por requisição

4. **Testes**
   - Testes unitários dos agentes
   - Testes de integração do workflow
   - Property-based tests para fallback

## Dependências

```toml
[tool.poetry.dependencies]
litellm = "^1.0.0"
langgraph = "^0.0.20"
openai = "^1.0.0"
anthropic = "^0.8.0"
google-generativeai = "^0.3.0"
```

## Exemplos de Uso Completo

### Exemplo 1: Qualificar Lead Automaticamente

```python
from app.ai.agents.maestro import MaestroAgent

async def process_new_lead(session, tenant_id, message, contact):
    maestro = MaestroAgent(session, tenant_id)
    
    result = await maestro.execute_workflow(
        task_type="qualificar_lead",
        initial_message="Qualificar este novo lead",
        context={
            "message": message,
            "contact": contact,
        },
    )
    
    # Criar lead no banco com dados extraídos
    lead = await create_lead(
        tenant_id=tenant_id,
        full_name=result.get("nome"),
        phone=result.get("telefone"),
        score=result.get("score"),
        stage="novo" if result.get("proxima_acao") == "solicitar_informacoes" else "qualificado",
    )
    
    return lead
```

### Exemplo 2: Gerar Briefing Diário

```python
from app.ai.workflows.morning_briefing import MorningBriefingWorkflow

async def generate_daily_briefing(session, tenant_id):
    workflow = MorningBriefingWorkflow(session, tenant_id)
    
    briefing = await workflow.generate_briefing(
        date_for=date.today(),
        hours_back=24,
    )
    
    # Salvar no banco
    await save_briefing(tenant_id, briefing)
    
    # Enviar por email
    await send_briefing_email(tenant_id, briefing)
    
    return briefing
```

### Exemplo 3: Analisar Processo com IA

```python
from app.ai.agents.investigator import InvestigadorAgent
from app.ai.agents.writer import RedatorAgent

async def analyze_and_summarize_process(session, tenant_id, process_id):
    # Buscar processo e movimentações
    process = await get_process(process_id)
    movements = await get_movements(process_id)
    
    # Analisar com Investigador
    investigador = InvestigadorAgent(session, tenant_id)
    analysis = await investigador.analyze_movements(
        process_info={"cnj_number": process.cnj_number},
        movements=[m.to_dict() for m in movements],
    )
    
    # Gerar resumo para cliente com Redator
    redator = RedatorAgent(session, tenant_id)
    summary = await redator.generate_movement_summary(
        movements=[m.to_dict() for m in movements],
        audience="cliente",
    )
    
    return {
        "analysis": analysis,
        "client_summary": summary,
    }
```

## Troubleshooting

### Provider Failures
```python
# Verificar status dos providers
manager = ProviderManager(session, tenant_id)
stats = await manager.get_usage_stats()
print(stats)  # {'openai/gpt-4': 150, 'google/gemini-pro': 20}

# Desabilitar provider problemático
await manager.toggle_provider(provider_id, is_active=False)
```

### Rate Limit Issues
```python
# Ajustar rate limit no config
settings.rate_limit_ai_per_minute = 20  # Aumentar limite

# Ou adicionar mais providers para distribuir carga
await manager.add_provider(
    provider="anthropic",
    model="claude-3-sonnet-20240229",
    api_key="...",
    priority=70,
)
```

### Circuit Breaker Triggered
```python
# O circuit breaker se recupera automaticamente após 60s
# Para forçar recuperação, reinicie o serviço ou aguarde

# Verificar logs
logger.info("Circuit breaker status", extra={
    "provider": "openai/gpt-4",
    "failures": 5,
    "is_open": True,
})
```

## Suporte

Para dúvidas ou problemas:
1. Verifique os logs estruturados
2. Consulte a documentação do LiteLLM
3. Revise as configurações de providers no banco
