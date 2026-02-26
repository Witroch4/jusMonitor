import { test, expect, helpers } from './fixtures/auth';
import {
  simulateChatwitWebhook,
  waitForWebhookProcessing,
  createChatwitMessagePayload,
  createChatwitTagPayload
} from './helpers/webhook-simulator';

/**
 * Testes E2E de integração com Chatwit
 * 
 * Valida:
 * - Requisito 2.1: Integração com Chatwit
 * - Webhook -> Lead criado -> Aparece no funil
 * - Tag adicionada -> Status atualizado
 */
test.describe('Integração Chatwit', () => {
  test('deve criar lead quando receber mensagem do Chatwit', async ({ authenticatedPage: page }) => {
    // 1. Navegar para o funil
    await page.goto('/funil');
    await helpers.waitForLoading(page);
    
    // 2. Contar leads atuais na coluna "Novo"
    const novoColumn = page.locator('[data-testid="column-novo"]');
    const initialLeads = await novoColumn.locator('[data-testid="lead-card"]').count();
    
    // 3. Simular webhook do Chatwit com nova mensagem
    const contactName = `Lead Teste ${Date.now()}`;
    const message = 'Olá, preciso de ajuda com um processo trabalhista';
    
    const payload = createChatwitMessagePayload(contactName, message);
    
    await simulateChatwitWebhook(page, payload);
    
    // 4. Aguardar processamento assíncrono
    await waitForWebhookProcessing(page, 3000);
    
    // 5. Recarregar página para ver novo lead
    await page.reload();
    await helpers.waitForLoading(page);
    
    // 6. Verificar que um novo lead foi criado
    const newLeadsCount = await novoColumn.locator('[data-testid="lead-card"]').count();
    expect(newLeadsCount).toBeGreaterThan(initialLeads);
    
    // 7. Verificar que o lead contém o nome correto
    const newLead = novoColumn.locator(`[data-testid="lead-card"]:has-text("${contactName}")`);
    await expect(newLead).toBeVisible();
  });
  
  test('deve qualificar lead automaticamente quando tag "qualificado" é adicionada', async ({ authenticatedPage: page }) => {
    // 1. Navegar para o funil
    await page.goto('/funil');
    await helpers.waitForLoading(page);
    
    // 2. Criar um lead primeiro
    const contactName = `Lead Auto Qualificado ${Date.now()}`;
    const messagePayload = createChatwitMessagePayload(contactName, 'Preciso de advogado');
    
    await simulateChatwitWebhook(page, messagePayload);
    await waitForWebhookProcessing(page, 2000);
    
    // 3. Recarregar para ver o lead
    await page.reload();
    await helpers.waitForLoading(page);
    
    // 4. Verificar que o lead está na coluna "Novo"
    const novoColumn = page.locator('[data-testid="column-novo"]');
    const leadInNovo = novoColumn.locator(`[data-testid="lead-card"]:has-text("${contactName}")`);
    await expect(leadInNovo).toBeVisible();
    
    // 5. Simular adição de tag "qualificado" no Chatwit
    const contactId = messagePayload.contact.id;
    const tagPayload = createChatwitTagPayload(contactId, 'qualificado');
    
    await simulateChatwitWebhook(page, tagPayload);
    await waitForWebhookProcessing(page, 3000);
    
    // 6. Recarregar página
    await page.reload();
    await helpers.waitForLoading(page);
    
    // 7. Verificar que o lead foi movido para "Qualificado"
    const qualificadoColumn = page.locator('[data-testid="column-qualificado"]');
    const leadInQualificado = qualificadoColumn.locator(`[data-testid="lead-card"]:has-text("${contactName}")`);
    await expect(leadInQualificado).toBeVisible();
  });
  
  test('deve criar lead com score alto para mensagens urgentes', async ({ authenticatedPage: page }) => {
    // 1. Navegar para o funil
    await page.goto('/funil');
    await helpers.waitForLoading(page);
    
    // 2. Simular mensagem urgente
    const contactName = `Lead Urgente ${Date.now()}`;
    const urgentMessage = 'URGENTE: Preciso de advogado imediatamente, tenho audiência amanhã!';
    
    const payload = createChatwitMessagePayload(contactName, urgentMessage);
    
    await simulateChatwitWebhook(page, payload);
    await waitForWebhookProcessing(page, 3000);
    
    // 3. Recarregar página
    await page.reload();
    await helpers.waitForLoading(page);
    
    // 4. Encontrar o lead criado
    const leadCard = page.locator(`[data-testid="lead-card"]:has-text("${contactName}")`);
    await expect(leadCard).toBeVisible();
    
    // 5. Clicar no lead para ver detalhes
    await leadCard.click();
    
    // 6. Verificar que o score é alto (> 70)
    const modal = page.locator('[data-testid="lead-details-modal"]');
    await expect(modal).toBeVisible();
    
    const scoreElement = modal.locator('[data-testid="lead-score"]');
    const scoreText = await scoreElement.textContent();
    
    if (scoreText) {
      const score = parseInt(scoreText.replace(/\D/g, ''));
      expect(score).toBeGreaterThan(70);
    }
  });
  
  test('deve atualizar lead existente quando receber nova mensagem do mesmo contato', async ({ authenticatedPage: page }) => {
    // 1. Criar lead inicial
    const contactName = `Lead Recorrente ${Date.now()}`;
    const contactId = `contact-${Date.now()}`;
    
    const firstMessage = createChatwitMessagePayload(contactName, 'Primeira mensagem');
    firstMessage.contact.id = contactId;
    
    await simulateChatwitWebhook(page, firstMessage);
    await waitForWebhookProcessing(page, 2000);
    
    // 2. Enviar segunda mensagem do mesmo contato
    const secondMessage = createChatwitMessagePayload(contactName, 'Segunda mensagem com mais detalhes');
    secondMessage.contact.id = contactId;
    
    await simulateChatwitWebhook(page, secondMessage);
    await waitForWebhookProcessing(page, 2000);
    
    // 3. Navegar para o funil
    await page.goto('/funil');
    await helpers.waitForLoading(page);
    
    // 4. Verificar que existe apenas um lead (não duplicado)
    const leadCards = page.locator(`[data-testid="lead-card"]:has-text("${contactName}")`);
    const count = await leadCards.count();
    
    expect(count).toBe(1);
    
    // 5. Verificar que o histórico contém ambas as mensagens
    await leadCards.first().click();
    
    const modal = page.locator('[data-testid="lead-details-modal"]');
    await expect(modal).toBeVisible();
    
    // Navegar para histórico se disponível
    const historyTab = modal.locator('[data-testid="history-tab"]');
    if (await historyTab.isVisible()) {
      await historyTab.click();
      
      const history = modal.locator('[data-testid="interaction-history"]');
      await expect(history).toContainText('Primeira mensagem');
      await expect(history).toContainText('Segunda mensagem');
    }
  });
  
  test('deve criar lead com informações de contato corretas', async ({ authenticatedPage: page }) => {
    // 1. Simular webhook com informações completas
    const contactName = `Lead Completo ${Date.now()}`;
    const phone = '+5511987654321';
    const email = 'lead.completo@example.com';
    
    const payload = createChatwitMessagePayload(contactName, 'Mensagem de teste');
    payload.contact.phone = phone;
    payload.contact.email = email;
    
    await simulateChatwitWebhook(page, payload);
    await waitForWebhookProcessing(page, 3000);
    
    // 2. Navegar para o funil
    await page.goto('/funil');
    await helpers.waitForLoading(page);
    
    // 3. Encontrar e clicar no lead
    const leadCard = page.locator(`[data-testid="lead-card"]:has-text("${contactName}")`);
    await expect(leadCard).toBeVisible();
    await leadCard.click();
    
    // 4. Verificar informações no modal
    const modal = page.locator('[data-testid="lead-details-modal"]');
    await expect(modal).toBeVisible();
    
    await expect(modal.locator('[data-testid="lead-name"]')).toContainText(contactName);
    await expect(modal.locator('[data-testid="lead-phone"]')).toContainText(phone);
    await expect(modal.locator('[data-testid="lead-email"]')).toContainText(email);
  });
});
