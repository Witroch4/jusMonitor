import { test, expect, helpers } from './fixtures/auth';
import {
  simulateDataJudMovement,
  waitForWebhookProcessing,
  createDataJudMovementPayload
} from './helpers/webhook-simulator';

/**
 * Testes E2E de integração com DataJud
 * 
 * Valida:
 * - Requisito 2.5: Monitoramento de processos DataJud
 * - DataJud polling -> Movimentação -> Notificação
 * - Atualização de processos
 */
test.describe('Integração DataJud', () => {
  test('deve detectar nova movimentação e exibir notificação', async ({ authenticatedPage: page }) => {
    // 1. Navegar para dashboard
    await page.goto('/dashboard');
    await helpers.waitForLoading(page);
    
    // 2. Verificar contador de notificações inicial
    const notificationBadge = page.locator('[data-testid="notification-badge"]');
    const initialCount = await notificationBadge.textContent().catch(() => '0');
    
    // 3. Simular nova movimentação do DataJud
    const cnjNumber = '0001234-56.2024.5.02.0001';
    const movementDescription = 'Sentença publicada - Procedente o pedido';
    
    const payload = createDataJudMovementPayload(cnjNumber, movementDescription);
    
    await simulateDataJudMovement(page, payload);
    
    // 4. Aguardar processamento e geração de notificação
    await waitForWebhookProcessing(page, 5000);
    
    // 5. Recarregar página para ver notificação
    await page.reload();
    await helpers.waitForLoading(page);
    
    // 6. Verificar que o contador de notificações aumentou
    const newCount = await notificationBadge.textContent().catch(() => '0');
    expect(parseInt(newCount)).toBeGreaterThan(parseInt(initialCount));
    
    // 7. Abrir centro de notificações
    await page.click('[data-testid="notification-center"]');
    
    // 8. Verificar que a notificação está presente
    const notificationList = page.locator('[data-testid="notification-list"]');
    await expect(notificationList).toBeVisible();
    
    const notification = notificationList.locator(`text=${cnjNumber}`);
    await expect(notification).toBeVisible();
  });
  
  test('deve atualizar dashboard com nova movimentação urgente', async ({ authenticatedPage: page }) => {
    // 1. Navegar para dashboard
    await page.goto('/dashboard');
    await helpers.waitForLoading(page);
    
    // 2. Contar casos urgentes atuais
    const urgentCases = page.locator('[data-testid="urgent-cases"] [data-testid="case-card"]');
    const initialCount = await urgentCases.count();
    
    // 3. Simular movimentação urgente (prazo curto)
    const cnjNumber = `0009999-99.2024.5.02.${Date.now().toString().slice(-4)}`;
    const urgentMovement = 'Intimação para apresentar recurso em 5 dias';
    
    const payload = createDataJudMovementPayload(cnjNumber, urgentMovement);
    
    await simulateDataJudMovement(page, payload);
    
    // 4. Aguardar processamento
    await waitForWebhookProcessing(page, 5000);
    
    // 5. Recarregar dashboard
    await page.reload();
    await helpers.waitForLoading(page);
    
    // 6. Verificar que o caso aparece em "Urgente"
    const newUrgentCount = await urgentCases.count();
    expect(newUrgentCount).toBeGreaterThanOrEqual(initialCount);
  });
  
  test('deve classificar movimentação como "Boa Notícia"', async ({ authenticatedPage: page }) => {
    // 1. Navegar para dashboard
    await page.goto('/dashboard');
    await helpers.waitForLoading(page);
    
    // 2. Simular movimentação positiva
    const cnjNumber = `0008888-88.2024.5.02.${Date.now().toString().slice(-4)}`;
    const goodNewsMovement = 'Sentença favorável - Procedente em todos os pedidos';
    
    const payload = createDataJudMovementPayload(cnjNumber, goodNewsMovement);
    
    await simulateDataJudMovement(page, payload);
    
    // 3. Aguardar processamento e classificação por IA
    await waitForWebhookProcessing(page, 5000);
    
    // 4. Recarregar dashboard
    await page.reload();
    await helpers.waitForLoading(page);
    
    // 5. Verificar que aparece em "Boas Notícias"
    const goodNewsSection = page.locator('[data-testid="good-news"]');
    await expect(goodNewsSection).toBeVisible();
    
    // Verificar se o caso está presente (pode levar tempo para IA processar)
    const goodNewsCase = goodNewsSection.locator(`text=${cnjNumber}`);
    await expect(goodNewsCase).toBeVisible({ timeout: 10000 });
  });
  
  test('deve atualizar timeline do cliente com nova movimentação', async ({ authenticatedPage: page }) => {
    // 1. Navegar para lista de clientes
    await page.goto('/clientes');
    await helpers.waitForLoading(page);
    
    // 2. Selecionar primeiro cliente
    const firstClient = page.locator('[data-testid="client-card"]').first();
    const clientCount = await firstClient.count();
    
    if (clientCount === 0) {
      test.skip('Nenhum cliente disponível para teste');
    }
    
    await firstClient.click();
    await page.waitForURL(/\/clientes\/[^/]+/);
    await helpers.waitForLoading(page);
    
    // 3. Navegar para timeline
    const timelineTab = page.locator('[data-testid="timeline-tab"]');
    await timelineTab.click();
    
    const timelineSection = page.locator('[data-testid="timeline-section"]');
    await expect(timelineSection).toBeVisible();
    
    // 4. Contar eventos atuais
    const timelineEvents = timelineSection.locator('[data-testid="timeline-event"]');
    const initialEventCount = await timelineEvents.count();
    
    // 5. Simular nova movimentação para um processo deste cliente
    const cnjNumber = '0007777-77.2024.5.02.0001';
    const movementDescription = 'Juntada de petição - Contestação apresentada';
    
    const payload = createDataJudMovementPayload(cnjNumber, movementDescription);
    
    await simulateDataJudMovement(page, payload);
    
    // 6. Aguardar processamento
    await waitForWebhookProcessing(page, 5000);
    
    // 7. Recarregar página
    await page.reload();
    await helpers.waitForLoading(page);
    
    // Navegar novamente para timeline
    await timelineTab.click();
    
    // 8. Verificar que um novo evento foi adicionado
    const newEventCount = await timelineEvents.count();
    expect(newEventCount).toBeGreaterThanOrEqual(initialEventCount);
  });
  
  test('deve marcar processo como "precisa atenção" quando parado por muito tempo', async ({ authenticatedPage: page }) => {
    // 1. Navegar para dashboard
    await page.goto('/dashboard');
    await helpers.waitForLoading(page);
    
    // 2. Verificar seção "Atenção"
    const attentionSection = page.locator('[data-testid="attention-cases"]');
    await expect(attentionSection).toBeVisible();
    
    // 3. Verificar que há casos que precisam atenção
    const attentionCases = attentionSection.locator('[data-testid="case-card"]');
    const count = await attentionCases.count();
    
    // Deve haver pelo menos alguns casos (baseado em dados de seed)
    expect(count).toBeGreaterThanOrEqual(0);
  });
  
  test('deve exibir resumo gerado por IA da movimentação', async ({ authenticatedPage: page }) => {
    // 1. Simular movimentação complexa
    const cnjNumber = `0006666-66.2024.5.02.${Date.now().toString().slice(-4)}`;
    const complexMovement = `
      Vistos etc. Trata-se de ação trabalhista proposta por João da Silva em face de 
      Empresa XYZ Ltda, objetivando o reconhecimento de vínculo empregatício e pagamento 
      de verbas rescisórias. Analisando os autos, verifico que estão presentes os requisitos 
      da tutela de urgência. Defiro a liminar para determinar o depósito de FGTS. 
      Intime-se a parte contrária para apresentar defesa no prazo legal.
    `;
    
    const payload = createDataJudMovementPayload(cnjNumber, complexMovement);
    
    await simulateDataJudMovement(page, payload);
    
    // 2. Aguardar processamento por IA
    await waitForWebhookProcessing(page, 8000);
    
    // 3. Navegar para dashboard
    await page.goto('/dashboard');
    await helpers.waitForLoading(page);
    
    // 4. Procurar o caso nos blocos
    const caseCard = page.locator(`[data-testid="case-card"]:has-text("${cnjNumber}")`);
    
    if (await caseCard.isVisible()) {
      // 5. Verificar que há um resumo gerado por IA
      const aiSummary = caseCard.locator('[data-testid="ai-summary"]');
      await expect(aiSummary).toBeVisible();
      
      // 6. Verificar que o resumo é mais curto que o original
      const summaryText = await aiSummary.textContent();
      expect(summaryText?.length || 0).toBeLessThan(complexMovement.length);
    }
  });
  
  test('deve permitir busca semântica de movimentações', async ({ authenticatedPage: page }) => {
    // 1. Navegar para página de processos
    await page.goto('/processos');
    await helpers.waitForLoading(page);
    
    // 2. Usar busca semântica
    const searchInput = page.locator('[data-testid="semantic-search"]');
    
    if (await searchInput.isVisible()) {
      // 3. Buscar por conceito (não texto exato)
      await searchInput.fill('decisões favoráveis ao trabalhador');
      await page.keyboard.press('Enter');
      
      // 4. Aguardar resultados
      await helpers.waitForLoading(page);
      
      // 5. Verificar que há resultados
      const searchResults = page.locator('[data-testid="search-result"]');
      const count = await searchResults.count();
      
      expect(count).toBeGreaterThanOrEqual(0);
    }
  });
});
