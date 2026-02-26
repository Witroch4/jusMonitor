# Taskiq Workers System

Sistema de processamento assíncrono de tarefas usando Taskiq com Redis.

## Arquitetura

### Componentes

1. **Broker** (`broker.py`): Configuração do broker Redis com middleware de logging
2. **Event Bus** (`events/`): Sistema de eventos com garantias at-least-once
3. **Base Tasks** (`tasks/base.py`): Infraestrutura base com decorators
4. **Worker Entry Point** (`main.py`): Ponto de entrada para workers

### Garantias

- **At-Least-Once Delivery**: Eventos são processados pelo menos uma vez
- **Retry com Backoff Exponencial**: Falhas são retentadas automaticamente
- **Dead Letter Queue**: Eventos que falham após max retries vão para DLQ
- **Rate Limiting**: Controle de taxa de execução por worker
- **Concurrency Control**: Limite de execuções concorrentes

## Uso

### 1. Criar uma Task

```python
from app.workers.broker import broker
from app.workers.tasks.base import with_retry, with_timeout, with_rate_limit

@broker.task
@with_retry(max_retries=3, backoff_factor=2.0)
@with_timeout(30.0)
@with_rate_limit(max_calls=100, period_seconds=60)
async def process_embedding(text: str, tenant_id: str):
    """Generate embedding for text."""
    # Task implementation
    embedding = await generate_embedding(text)
    return embedding
```

### 2. Enfileirar uma Task

```python
# Enqueue task for async processing
await process_embedding.kiq(
    text="Sample text",
    tenant_id="123e4567-e89b-12d3-a456-426614174000"
)
```

### 3. Publicar Eventos

```python
from app.workers.events import publish, LeadCreatedEvent
from uuid import uuid4

# Create and publish event
event = LeadCreatedEvent(
    tenant_id=uuid4(),
    lead_id=uuid4(),
    source="chatwit",
    score=75
)

await publish(event)
```

### 4. Subscrever a Eventos

```python
from app.workers.events import subscribe, EventType, LeadCreatedEvent

@subscribe(EventType.LEAD_CREATED)
async def handle_lead_created(event_data: dict):
    """Handle lead creation event."""
    lead_id = event_data["lead_id"]
    tenant_id = event_data["tenant_id"]
    
    # Process event
    await send_welcome_message(lead_id)
    await calculate_lead_score(lead_id)
```

### 5. Usar BaseTask

```python
from app.workers.tasks.base import BaseTask

class EmbeddingTask(BaseTask):
    def __init__(self):
        super().__init__(task_name="embedding_generation")
    
    async def execute(self, text: str, tenant_id: str):
        """Generate embedding."""
        self.logger.info("generating_embedding", text_length=len(text))
        
        embedding = await self._generate(text)
        
        self.logger.info("embedding_generated", dimension=len(embedding))
        return embedding
    
    async def _generate(self, text: str):
        # Implementation
        pass

# Use the task
task = EmbeddingTask()
result = await task(text="Sample", tenant_id="...")
```

### 6. Controlar Concorrência

```python
from app.workers.tasks.base import TaskConcurrencyLimiter

async def process_batch():
    # Limit to 5 concurrent executions
    async with TaskConcurrencyLimiter(
        max_concurrent=5,
        key_prefix="datajud_sync"
    ):
        # Process batch
        await sync_processes()
```

## Executar Workers

### Desenvolvimento

```bash
# Start worker
taskiq worker app.workers.main:broker

# With auto-reload
taskiq worker app.workers.main:broker --reload

# Multiple workers
taskiq worker app.workers.main:broker --workers 4
```

### Produção

```bash
# With systemd or supervisor
taskiq worker app.workers.main:broker \
    --workers 4 \
    --log-level INFO
```

### Docker

```yaml
# docker-compose.yml
services:
  worker:
    build: .
    command: taskiq worker app.workers.main:broker --workers 4
    environment:
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis
```

## Dead Letter Queue

### Visualizar Eventos Falhados

```python
from app.workers.events.bus import get_dlq_events

# Get all failed events
events = await get_dlq_events(limit=100)

# Get failed events by type
events = await get_dlq_events(
    event_type=EventType.LEAD_CREATED,
    limit=50
)
```

### Reprocessar Evento

```python
from app.workers.events.bus import retry_dlq_event

# Retry specific event
success = await retry_dlq_event(event_id="...")
```

## Monitoramento

### Logs Estruturados

Todos os eventos são logados com contexto:

```json
{
  "event": "task_started",
  "task_name": "process_embedding",
  "task_id": "abc123",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Métricas

- Task execution time
- Task success/failure rate
- Retry attempts
- DLQ size
- Rate limit hits

## Boas Práticas

1. **Idempotência**: Tasks devem ser idempotentes (podem ser executadas múltiplas vezes)
2. **Timeout**: Sempre definir timeout para evitar tasks travadas
3. **Retry**: Usar retry apenas para erros transientes
4. **Logging**: Usar structured logging para facilitar debugging
5. **Rate Limiting**: Respeitar limites de APIs externas
6. **Concurrency**: Limitar concorrência para operações pesadas

## Exemplos Completos

### Worker de Embeddings

```python
from app.workers.broker import broker
from app.workers.tasks.base import with_retry, with_timeout

@broker.task
@with_retry(max_retries=3)
@with_timeout(60.0)
async def generate_embeddings_batch(texts: list[str], tenant_id: str):
    """Generate embeddings for batch of texts."""
    from app.core.services.embedding_service import EmbeddingService
    
    service = EmbeddingService()
    embeddings = await service.generate_batch(texts)
    
    # Store in database
    await store_embeddings(embeddings, tenant_id)
    
    return len(embeddings)
```

### Worker de Sincronização DataJud

```python
from app.workers.broker import broker
from app.workers.tasks.base import with_retry, with_rate_limit

@broker.task
@with_retry(max_retries=5, backoff_factor=2.0)
@with_rate_limit(max_calls=1, period_seconds=36)  # 100 req/hour
async def sync_process_batch(process_ids: list[str], tenant_id: str):
    """Sync batch of processes from DataJud."""
    from app.core.services.datajud_service import DataJudService
    
    service = DataJudService()
    
    for process_id in process_ids:
        movements = await service.get_movements(process_id)
        await process_movements(movements, tenant_id)
```

### Handler de Eventos

```python
from app.workers.events import subscribe, EventType, MovementDetectedEvent
from app.workers.broker import broker

@subscribe(EventType.MOVEMENT_DETECTED)
async def handle_movement_detected(event_data: dict):
    """Handle new movement detection."""
    movement_id = event_data["movement_id"]
    process_id = event_data["process_id"]
    
    # Enqueue embedding generation
    await generate_movement_embedding.kiq(
        movement_id=movement_id,
        process_id=process_id
    )
    
    # If important, send notification
    if event_data.get("is_important"):
        await send_notification.kiq(
            process_id=process_id,
            movement_id=movement_id
        )

@broker.task
async def generate_movement_embedding(movement_id: str, process_id: str):
    """Generate embedding for movement."""
    # Implementation
    pass

@broker.task
async def send_notification(process_id: str, movement_id: str):
    """Send notification about movement."""
    # Implementation
    pass
```

## Troubleshooting

### Worker não inicia

- Verificar conexão com Redis
- Verificar variáveis de ambiente
- Verificar logs de erro

### Tasks não são executadas

- Verificar se worker está rodando
- Verificar se tasks foram importadas em `main.py`
- Verificar logs do worker

### DLQ crescendo

- Investigar causa das falhas
- Corrigir código ou dados
- Reprocessar eventos após correção

### Rate limit atingido

- Ajustar `max_calls` e `period_seconds`
- Distribuir carga entre mais workers
- Implementar batching
