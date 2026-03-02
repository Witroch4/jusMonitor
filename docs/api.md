# JusMonitorIA API Documentation

## Visão Geral

A API do JusMonitorIA é uma API REST construída com FastAPI que fornece acesso completo às funcionalidades do sistema de CRM jurídico.

**Base URL**: `http://localhost:8000` (desenvolvimento) ou `https://api.jusmonitoria.com` (produção)

**Versão**: v1

**Formato**: JSON

## Autenticação

### JWT (JSON Web Token)

Todos os endpoints (exceto `/auth/login` e webhooks) requerem autenticação via JWT Bearer token.

#### Obter Token

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "usuario@exemplo.com",
  "password": "senha123"
}
```

**Resposta:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

#### Usar Token

Inclua o token no header `Authorization` de todas as requisições:

```http
GET /api/v1/clients
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### Refresh Token

Quando o `access_token` expirar, use o `refresh_token` para obter um novo:

```http
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

## Endpoints

### Autenticação

#### POST /api/v1/auth/login

Autentica um usuário e retorna tokens JWT.

**Request:**

```json
{
  "email": "usuario@exemplo.com",
  "password": "senha123"
}
```

**Response (200):**

```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": "uuid",
    "email": "usuario@exemplo.com",
    "full_name": "João Silva",
    "role": "advogado",
    "tenant_id": "uuid"
  }
}
```

#### POST /api/v1/auth/refresh

Renova o access token usando o refresh token.

**Request:**

```json
{
  "refresh_token": "eyJ..."
}
```

**Response (200):**

```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

#### POST /api/v1/auth/logout

Invalida o token atual (logout).

**Headers:**
- `Authorization: Bearer <token>`

**Response (204):** No content

---

### Leads

#### GET /api/v1/leads

Lista todos os leads do tenant.

**Query Parameters:**
- `stage` (opcional): Filtrar por estágio (`novo`, `qualificado`, `convertido`)
- `source` (opcional): Filtrar por origem (`chatwit`, `website`, `indicacao`)
- `score_min` (opcional): Score mínimo (0-100)
- `score_max` (opcional): Score máximo (0-100)
- `limit` (opcional): Itens por página (padrão: 20, máximo: 100)
- `offset` (opcional): Número de itens para pular (padrão: 0)
- `sort_by` (opcional): Campo para ordenação (`created_at`, `score`, `full_name`)
- `sort_order` (opcional): Ordem (`asc` ou `desc`, padrão: `desc`)

**Response (200):**

```json
{
  "items": [
    {
      "id": "uuid",
      "tenant_id": "uuid",
      "full_name": "Maria Santos",
      "phone": "+5511999999999",
      "email": "maria@exemplo.com",
      "source": "chatwit",
      "stage": "qualificado",
      "score": 85,
      "ai_summary": "Lead qualificado com alta probabilidade de conversão...",
      "ai_recommended_action": "agendar_reuniao",
      "assigned_to": "uuid",
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T14:20:00Z"
    }
  ],
  "total": 42,
  "limit": 20,
  "offset": 0,
  "has_more": true
}
```

#### POST /api/v1/leads

Cria um novo lead.

**Request:**

```json
{
  "full_name": "Maria Santos",
  "phone": "+5511999999999",
  "email": "maria@exemplo.com",
  "source": "chatwit",
  "chatwit_contact_id": "chatwit_123"
}
```

**Response (201):**

```json
{
  "id": "uuid",
  "tenant_id": "uuid",
  "full_name": "Maria Santos",
  "phone": "+5511999999999",
  "email": "maria@exemplo.com",
  "source": "chatwit",
  "stage": "novo",
  "score": 0,
  "created_at": "2024-01-15T10:30:00Z"
}
```

#### GET /api/v1/leads/{lead_id}

Obtém detalhes de um lead específico.

**Response (200):**

```json
{
  "id": "uuid",
  "tenant_id": "uuid",
  "full_name": "Maria Santos",
  "phone": "+5511999999999",
  "email": "maria@exemplo.com",
  "source": "chatwit",
  "stage": "qualificado",
  "score": 85,
  "ai_summary": "Lead qualificado...",
  "ai_recommended_action": "agendar_reuniao",
  "assigned_to": {
    "id": "uuid",
    "full_name": "João Advogado",
    "email": "joao@escritorio.com"
  },
  "timeline": [
    {
      "id": "uuid",
      "event_type": "lead_created",
      "title": "Lead criado",
      "created_at": "2024-01-15T10:30:00Z"
    }
  ],
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T14:20:00Z"
}
```

#### PATCH /api/v1/leads/{lead_id}/stage

Atualiza o estágio do lead (usado no drag-and-drop do Kanban).

**Request:**

```json
{
  "stage": "qualificado"
}
```

**Response (200):**

```json
{
  "id": "uuid",
  "stage": "qualificado",
  "updated_at": "2024-01-15T14:20:00Z"
}
```

#### POST /api/v1/leads/{lead_id}/convert

Converte um lead em cliente.

**Request:**

```json
{
  "cpf_cnpj": "12345678900",
  "address": {
    "street": "Rua Exemplo, 123",
    "city": "São Paulo",
    "state": "SP",
    "zip_code": "01234-567"
  }
}
```

**Response (201):**

```json
{
  "client": {
    "id": "uuid",
    "full_name": "Maria Santos",
    "cpf_cnpj": "12345678900",
    "email": "maria@exemplo.com",
    "phone": "+5511999999999",
    "status": "active",
    "created_at": "2024-01-15T15:00:00Z"
  },
  "lead": {
    "id": "uuid",
    "stage": "convertido",
    "converted_at": "2024-01-15T15:00:00Z",
    "converted_to_client_id": "uuid"
  }
}
```

---

### Clientes

#### GET /api/v1/clients

Lista todos os clientes do tenant.

**Query Parameters:**
- `status` (opcional): Filtrar por status (`active`, `inactive`, `archived`)
- `assigned_to` (opcional): Filtrar por advogado responsável (UUID)
- `search` (opcional): Busca por nome, CPF/CNPJ ou email
- `limit`, `offset`, `sort_by`, `sort_order`: Paginação e ordenação

**Response (200):**

```json
{
  "items": [
    {
      "id": "uuid",
      "tenant_id": "uuid",
      "full_name": "Maria Santos",
      "cpf_cnpj": "12345678900",
      "email": "maria@exemplo.com",
      "phone": "+5511999999999",
      "status": "active",
      "health_score": 85,
      "assigned_to": {
        "id": "uuid",
        "full_name": "João Advogado"
      },
      "processes_count": 3,
      "last_interaction": "2024-01-15T14:20:00Z",
      "created_at": "2024-01-10T10:00:00Z"
    }
  ],
  "total": 127,
  "limit": 20,
  "offset": 0,
  "has_more": true
}
```

#### GET /api/v1/clients/{client_id}

Obtém prontuário 360º do cliente.

**Response (200):**

```json
{
  "id": "uuid",
  "tenant_id": "uuid",
  "full_name": "Maria Santos",
  "cpf_cnpj": "12345678900",
  "email": "maria@exemplo.com",
  "phone": "+5511999999999",
  "address": {
    "street": "Rua Exemplo, 123",
    "city": "São Paulo",
    "state": "SP",
    "zip_code": "01234-567"
  },
  "status": "active",
  "health_score": 85,
  "assigned_to": {
    "id": "uuid",
    "full_name": "João Advogado",
    "email": "joao@escritorio.com"
  },
  "processes": [
    {
      "id": "uuid",
      "cnj_number": "0000000-00.0000.0.00.0000",
      "court": "TJSP",
      "status": "Em andamento",
      "last_movement_date": "2024-01-14T00:00:00Z"
    }
  ],
  "automations": {
    "briefing_matinal": true,
    "alertas_urgentes": true,
    "resumo_semanal": false
  },
  "created_at": "2024-01-10T10:00:00Z",
  "updated_at": "2024-01-15T14:20:00Z"
}
```

#### GET /api/v1/clients/{client_id}/timeline

Obtém timeline de eventos do cliente.

**Query Parameters:**
- `event_type` (opcional): Filtrar por tipo de evento
- `limit`, `offset`: Paginação

**Response (200):**

```json
{
  "items": [
    {
      "id": "uuid",
      "event_type": "movement_detected",
      "title": "Nova movimentação no processo 0000000-00.0000.0.00.0000",
      "description": "Sentença publicada",
      "metadata": {
        "process_id": "uuid",
        "movement_id": "uuid",
        "is_important": true
      },
      "source": "datajud",
      "created_at": "2024-01-15T14:20:00Z"
    }
  ],
  "total": 156,
  "limit": 50,
  "offset": 0,
  "has_more": true
}
```

#### GET /api/v1/clients/{client_id}/health

Obtém painel de saúde do cliente.

**Response (200):**

```json
{
  "client_id": "uuid",
  "health_score": 85,
  "factors": {
    "activity": {
      "score": 90,
      "description": "Cliente ativo com interações recentes"
    },
    "satisfaction": {
      "score": 80,
      "description": "Satisfação estimada baseada em interações"
    },
    "risk": {
      "score": 85,
      "description": "Baixo risco de churn"
    }
  },
  "alerts": [
    {
      "type": "deadline_approaching",
      "severity": "high",
      "message": "Prazo de recurso em 3 dias",
      "process_id": "uuid"
    }
  ],
  "recommendations": [
    {
      "action": "schedule_meeting",
      "reason": "Sem contato há 15 dias",
      "priority": "medium"
    }
  ],
  "calculated_at": "2024-01-15T15:00:00Z"
}
```

#### PUT /api/v1/clients/{client_id}/automations

Configura automações do cliente.

**Request:**

```json
{
  "briefing_matinal": true,
  "alertas_urgentes": true,
  "resumo_semanal": false
}
```

**Response (200):**

```json
{
  "client_id": "uuid",
  "automations": {
    "briefing_matinal": true,
    "alertas_urgentes": true,
    "resumo_semanal": false
  },
  "updated_at": "2024-01-15T15:00:00Z"
}
```

---

### Dashboard (Central Operacional)

#### GET /api/v1/dashboard/urgent

Lista casos urgentes (prazo < 3 dias).

**Response (200):**

```json
{
  "items": [
    {
      "process_id": "uuid",
      "client_id": "uuid",
      "client_name": "Maria Santos",
      "cnj_number": "0000000-00.0000.0.00.0000",
      "court": "TJSP",
      "deadline": "2024-01-17T23:59:59Z",
      "days_remaining": 2,
      "action_required": "Apresentar recurso",
      "priority": "critical"
    }
  ],
  "total": 5
}
```

#### GET /api/v1/dashboard/attention

Lista casos que precisam atenção (parados > 30 dias).

**Response (200):**

```json
{
  "items": [
    {
      "process_id": "uuid",
      "client_id": "uuid",
      "client_name": "João Silva",
      "cnj_number": "0000000-00.0000.0.00.0000",
      "court": "TJRJ",
      "last_movement_date": "2023-12-01T00:00:00Z",
      "days_since_last_movement": 45,
      "reason": "Processo parado há mais de 30 dias"
    }
  ],
  "total": 12
}
```

#### GET /api/v1/dashboard/good-news

Lista boas notícias (decisões favoráveis).

**Response (200):**

```json
{
  "items": [
    {
      "process_id": "uuid",
      "client_id": "uuid",
      "client_name": "Ana Costa",
      "cnj_number": "0000000-00.0000.0.00.0000",
      "movement_type": "Sentença",
      "summary": "Sentença favorável ao cliente",
      "ai_analysis": "Decisão procedente com condenação da parte contrária...",
      "date": "2024-01-15T00:00:00Z"
    }
  ],
  "total": 3
}
```

#### GET /api/v1/dashboard/noise

Lista ruído (movimentações irrelevantes).

**Response (200):**

```json
{
  "items": [
    {
      "process_id": "uuid",
      "cnj_number": "0000000-00.0000.0.00.0000",
      "movement_type": "Juntada",
      "description": "Juntada de documento administrativo",
      "date": "2024-01-15T00:00:00Z",
      "reason": "Movimentação classificada como irrelevante pela IA"
    }
  ],
  "total": 28
}
```

#### GET /api/v1/dashboard/metrics

Obtém métricas do escritório.

**Query Parameters:**
- `period` (opcional): Período de análise (`7d`, `30d`, `90d`, padrão: `30d`)

**Response (200):**

```json
{
  "period": "30d",
  "leads": {
    "total": 156,
    "converted": 23,
    "conversion_rate": 14.7,
    "change_from_previous": 5.2
  },
  "clients": {
    "total": 127,
    "active": 115,
    "new_this_period": 23,
    "churn_rate": 2.1
  },
  "processes": {
    "total": 342,
    "active": 298,
    "new_this_period": 15,
    "closed_this_period": 8
  },
  "response_time": {
    "average_hours": 4.2,
    "median_hours": 2.5,
    "change_from_previous": -12.3
  },
  "satisfaction": {
    "score": 8.7,
    "responses": 45,
    "change_from_previous": 3.5
  },
  "calculated_at": "2024-01-15T15:00:00Z"
}
```

---

### Webhooks

#### POST /webhooks/chatwit

Recebe webhooks do Chatwit.

**Headers:**
- `X-Chatwit-Signature`: Assinatura HMAC para validação

**Request:**

```json
{
  "event_type": "message.received",
  "timestamp": "2024-01-15T15:00:00Z",
  "contact": {
    "id": "chatwit_123",
    "name": "Maria Santos",
    "phone": "+5511999999999",
    "email": "maria@exemplo.com"
  },
  "message": {
    "id": "msg_123",
    "direction": "inbound",
    "content": "Olá, gostaria de informações sobre divórcio",
    "channel": "whatsapp"
  }
}
```

**Response (200):**

```json
{
  "status": "received",
  "event_id": "uuid"
}
```

---

### Health Checks

#### GET /health/live

Liveness probe (verifica se aplicação está rodando).

**Response (200):**

```json
{
  "status": "ok"
}
```

#### GET /health/ready

Readiness probe (verifica se aplicação está pronta para receber tráfego).

**Response (200):**

```json
{
  "status": "ok",
  "checks": {
    "database": "ok",
    "redis": "ok",
    "chatwit_api": "ok",
    "datajud_api": "ok"
  }
}
```

**Response (503) - Quando algum serviço está indisponível:**

```json
{
  "status": "unavailable",
  "checks": {
    "database": "ok",
    "redis": "error",
    "chatwit_api": "ok",
    "datajud_api": "timeout"
  }
}
```

---

### Métricas

#### GET /metrics

Endpoint de métricas Prometheus.

**Response (200):** Formato Prometheus

```
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",endpoint="/api/v1/clients",status="200"} 1523

# HELP http_request_duration_seconds HTTP request duration
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{le="0.1"} 1234
http_request_duration_seconds_bucket{le="0.5"} 1456
http_request_duration_seconds_sum 234.5
http_request_duration_seconds_count 1523
```

---

## Códigos de Erro

### 400 Bad Request

Dados inválidos na requisição.

```json
{
  "detail": "Invalid request data",
  "errors": [
    {
      "field": "email",
      "message": "Invalid email format"
    }
  ]
}
```

### 401 Unauthorized

Token ausente ou inválido.

```json
{
  "detail": "Could not validate credentials"
}
```

### 403 Forbidden

Usuário não tem permissão para acessar o recurso.

```json
{
  "detail": "Insufficient permissions"
}
```

### 404 Not Found

Recurso não encontrado.

```json
{
  "detail": "Client not found"
}
```

### 409 Conflict

Conflito (ex: tentativa de criar recurso duplicado).

```json
{
  "detail": "Client with this CPF already exists"
}
```

### 422 Unprocessable Entity

Validação de schema falhou.

```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### 429 Too Many Requests

Rate limit excedido.

```json
{
  "detail": "Rate limit exceeded. Try again in 60 seconds."
}
```

**Headers:**
- `Retry-After: 60`

### 500 Internal Server Error

Erro interno do servidor.

```json
{
  "detail": "Internal server error",
  "request_id": "uuid"
}
```

---

## Rate Limiting

A API implementa rate limiting para proteger contra abuso:

| Endpoint | Limite |
|----------|--------|
| Geral | 100 req/min |
| `/auth/login` | 5 req/min |
| Endpoints de IA | 10 req/min |

Quando o limite é excedido, a API retorna `429 Too Many Requests` com header `Retry-After` indicando quantos segundos aguardar.

---

## Paginação

Endpoints de listagem retornam dados paginados:

**Query Parameters:**
- `limit`: Itens por página (padrão: 20, máximo: 100)
- `offset`: Número de itens para pular (padrão: 0)

**Response:**

```json
{
  "items": [...],
  "total": 156,
  "limit": 20,
  "offset": 40,
  "has_more": true
}
```

---

## Filtros e Ordenação

**Filtros:**

Cada endpoint de listagem suporta filtros específicos via query parameters.

**Ordenação:**

- `sort_by`: Campo para ordenação
- `sort_order`: `asc` ou `desc` (padrão: `desc`)

Exemplo:

```
GET /api/v1/clients?sort_by=created_at&sort_order=desc
```

---

## WebSocket (Notificações em Tempo Real)

### Conectar

```javascript
const ws = new WebSocket('ws://localhost:8000/ws?token=<jwt_token>');

ws.onopen = () => {
  console.log('Connected');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Notification:', data);
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = () => {
  console.log('Disconnected');
};
```

### Mensagens Recebidas

```json
{
  "type": "movement_detected",
  "data": {
    "process_id": "uuid",
    "client_id": "uuid",
    "client_name": "Maria Santos",
    "cnj_number": "0000000-00.0000.0.00.0000",
    "movement_type": "Sentença",
    "is_important": true,
    "summary": "Sentença favorável ao cliente"
  },
  "timestamp": "2024-01-15T15:00:00Z"
}
```

---

## Exemplos de Uso

### Exemplo 1: Autenticar e Listar Clientes

```bash
# 1. Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@demo.com","password":"admin123"}'

# Resposta: { "access_token": "eyJ...", ... }

# 2. Listar clientes
curl -X GET http://localhost:8000/api/v1/clients \
  -H "Authorization: Bearer eyJ..."
```

### Exemplo 2: Criar Lead e Converter em Cliente

```bash
# 1. Criar lead
curl -X POST http://localhost:8000/api/v1/leads \
  -H "Authorization: Bearer eyJ..." \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Maria Santos",
    "phone": "+5511999999999",
    "email": "maria@exemplo.com",
    "source": "website"
  }'

# Resposta: { "id": "lead-uuid", ... }

# 2. Converter em cliente
curl -X POST http://localhost:8000/api/v1/leads/lead-uuid/convert \
  -H "Authorization: Bearer eyJ..." \
  -H "Content-Type: application/json" \
  -d '{
    "cpf_cnpj": "12345678900",
    "address": {
      "street": "Rua Exemplo, 123",
      "city": "São Paulo",
      "state": "SP",
      "zip_code": "01234-567"
    }
  }'
```

### Exemplo 3: Obter Dashboard

```bash
# Casos urgentes
curl -X GET http://localhost:8000/api/v1/dashboard/urgent \
  -H "Authorization: Bearer eyJ..."

# Métricas do escritório
curl -X GET "http://localhost:8000/api/v1/dashboard/metrics?period=30d" \
  -H "Authorization: Bearer eyJ..."
```

---

## Documentação Interativa

Acesse a documentação interativa em:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

Você pode testar todos os endpoints diretamente pela interface do Swagger UI.

---

## Suporte

Para dúvidas ou problemas com a API:

- **Email**: suporte@jusmonitoria.com
- **Documentação**: https://docs.jusmonitoria.com
- **Status**: https://status.jusmonitoria.com
