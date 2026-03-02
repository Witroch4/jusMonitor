# Testes E2E - JusMonitorIA Frontend

Este diretório contém os testes End-to-End (E2E) do frontend do JusMonitorIA, implementados com Playwright.

## Estrutura

```
e2e/
├── fixtures/
│   └── auth.ts              # Fixtures de autenticação
├── helpers/
│   └── webhook-simulator.ts # Simulador de webhooks
├── 01-dashboard-flow.spec.ts      # Testes do fluxo de dashboard
├── 02-funnel-flow.spec.ts         # Testes do funil Kanban
├── 03-prontuario-flow.spec.ts     # Testes do prontuário 360º
├── 04-chatwit-integration.spec.ts # Testes de integração Chatwit
├── 05-datajud-integration.spec.ts # Testes de integração DataJud
├── 06-briefing-integration.spec.ts # Testes do briefing matinal
├── global-setup.ts          # Setup global dos testes
└── README.md               # Este arquivo
```

## Pré-requisitos

1. **Backend rodando**: Os testes E2E precisam que o backend esteja disponível
2. **Dados de seed**: Execute os seeds para ter dados de teste
3. **Playwright instalado**: `npm install` já instala o Playwright

## Instalação

```bash
# Instalar dependências (se ainda não instalou)
npm install

# Instalar browsers do Playwright
npx playwright install
```

## Executando os Testes

### Todos os testes

```bash
npm run test:e2e
```

### Modo UI (interativo)

```bash
npm run test:e2e:ui
```

### Modo headed (ver o browser)

```bash
npm run test:e2e:headed
```

### Modo debug

```bash
npm run test:e2e:debug
```

### Teste específico

```bash
npx playwright test 01-dashboard-flow.spec.ts
```

### Apenas um browser

```bash
npx playwright test --project=chromium
```

## Visualizar Relatório

Após executar os testes, você pode visualizar o relatório HTML:

```bash
npm run test:e2e:report
```

## Estrutura dos Testes

### 1. Dashboard Flow (01-dashboard-flow.spec.ts)

Testa o fluxo principal:
- Login → Dashboard → Ver caso urgente
- Filtros e navegação
- Métricas do escritório

**Requisitos validados**: 4.1 (Dashboard/Central Operacional)

### 2. Funnel Flow (02-funnel-flow.spec.ts)

Testa o funil Kanban:
- Visualização de leads
- Drag and drop entre colunas
- Conversão de lead para cliente
- Filtros e busca

**Requisitos validados**: 2.2 (Gestão de Leads), 3.3 (Conversão)

### 3. Prontuário Flow (03-prontuario-flow.spec.ts)

Testa o prontuário 360º:
- Navegação entre seções
- Ativação de automações
- Visualização de timeline
- Criação de notas internas

**Requisitos validados**: 3.3 (Automações), 3.2 (Timeline)

### 4. Chatwit Integration (04-chatwit-integration.spec.ts)

Testa integração com Chatwit:
- Webhook → Lead criado → Aparece no funil
- Tag adicionada → Status atualizado
- Qualificação automática

**Requisitos validados**: 2.1 (Integração Chatwit)

### 5. DataJud Integration (05-datajud-integration.spec.ts)

Testa integração com DataJud:
- Polling → Movimentação → Notificação
- Atualização de processos
- Classificação por IA
- Busca semântica

**Requisitos validados**: 2.5 (Monitoramento DataJud)

### 6. Briefing Integration (06-briefing-integration.spec.ts)

Testa briefing matinal:
- Geração automática
- Classificação em 4 blocos
- Métricas e comparações
- Atualização em tempo real

**Requisitos validados**: 2.8 (Briefing matinal)

## Fixtures e Helpers

### Auth Fixtures (fixtures/auth.ts)

Fornece páginas pré-autenticadas:

```typescript
test('meu teste', async ({ authenticatedPage: page }) => {
  // Página já está autenticada como advogado
  await page.goto('/dashboard');
});
```

Fixtures disponíveis:
- `authenticatedPage`: Autenticado como advogado (padrão)
- `adminPage`: Autenticado como admin
- `lawyerPage`: Autenticado como advogado

### Webhook Simulator (helpers/webhook-simulator.ts)

Simula webhooks de integrações externas:

```typescript
import { simulateChatwitWebhook, createChatwitMessagePayload } from './helpers/webhook-simulator';

// Simular mensagem do Chatwit
const payload = createChatwitMessagePayload('João Silva', 'Preciso de advogado');
await simulateChatwitWebhook(page, payload);
```

## Credenciais de Teste

As credenciais estão definidas em `fixtures/auth.ts`:

- **Admin**: admin@demo.com / admin123
- **Advogado**: advogado@demo.com / lawyer123
- **Assistente**: assistente@demo.com / assistant123

## Configuração

A configuração do Playwright está em `playwright.config.ts`:

- **Base URL**: http://localhost:3000 (configurável via `PLAYWRIGHT_BASE_URL`)
- **Timeout**: 30 segundos por teste
- **Retry**: 2 tentativas no CI, 0 localmente
- **Browsers**: Chromium, Firefox, WebKit, Mobile Chrome, Mobile Safari

## Boas Práticas

1. **Use data-testid**: Sempre use `data-testid` para selecionar elementos
2. **Aguarde loading**: Use `helpers.waitForLoading(page)` após navegação
3. **Verifique visibilidade**: Use `await expect(element).toBeVisible()`
4. **Evite timeouts fixos**: Prefira `waitForSelector` ao invés de `waitForTimeout`
5. **Isole testes**: Cada teste deve ser independente

## Troubleshooting

### Testes falhando por timeout

- Verifique se o backend está rodando
- Aumente o timeout em `playwright.config.ts`
- Use `--headed` para ver o que está acontecendo

### Elementos não encontrados

- Verifique se os `data-testid` estão corretos
- Use `page.pause()` para debugar
- Verifique se o loading terminou

### Webhooks não funcionando

- Verifique se o backend tem endpoints de webhook
- Verifique logs do backend
- Use modo debug para ver requisições

## CI/CD

Os testes E2E devem ser executados no CI após:
1. Build do frontend
2. Inicialização do backend
3. Execução dos seeds

Exemplo de workflow:

```yaml
- name: Run E2E tests
  run: |
    npm run test:e2e
  env:
    PLAYWRIGHT_BASE_URL: http://localhost:3000
```

## Relatórios

Os relatórios são gerados em:
- `playwright-report/`: Relatório HTML
- `test-results/`: Screenshots e vídeos de falhas

## Contribuindo

Ao adicionar novos testes:

1. Siga a convenção de nomenclatura: `XX-nome-do-fluxo.spec.ts`
2. Documente os requisitos validados
3. Use fixtures e helpers existentes
4. Adicione comentários explicativos
5. Teste localmente antes de commitar

## Recursos

- [Documentação Playwright](https://playwright.dev)
- [Best Practices](https://playwright.dev/docs/best-practices)
- [API Reference](https://playwright.dev/docs/api/class-playwright)
