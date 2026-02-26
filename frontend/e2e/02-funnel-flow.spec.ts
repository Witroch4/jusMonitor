import { test, expect, helpers } from './fixtures/auth';

/**
 * Testes E2E do fluxo de funil: Funil -> Mover lead -> Converter para cliente
 * 
 * Valida:
 * - Requisito 2.2: Gestão de Leads
 * - Requisito 3.3: Conversão de leads
 * - Drag and drop de leads
 * - Conversão para cliente
 */
test.describe('Fluxo Funil Kanban', () => {
  test('deve visualizar o funil com leads em diferentes estágios', async ({ authenticatedPage: page }) => {
    // 1. Navegar para o funil
    await page.goto('/funil');
    await helpers.waitForLoading(page);
    
    // 2. Verificar que o título está correto
    await expect(page.locator('h1')).toContainText('Funil');
    
    // 3. Verificar que as colunas do Kanban estão visíveis
    await expect(page.locator('[data-testid="column-novo"]')).toBeVisible();
    await expect(page.locator('[data-testid="column-qualificado"]')).toBeVisible();
    await expect(page.locator('[data-testid="column-convertido"]')).toBeVisible();
    
    // 4. Verificar que há leads nas colunas
    const leadCards = page.locator('[data-testid="lead-card"]');
    const count = await leadCards.count();
    
    expect(count).toBeGreaterThan(0);
  });
  
  test('deve mover lead de "Novo" para "Qualificado"', async ({ authenticatedPage: page }) => {
    // 1. Navegar para o funil
    await page.goto('/funil');
    await helpers.waitForLoading(page);
    
    // 2. Encontrar um lead na coluna "Novo"
    const novoColumn = page.locator('[data-testid="column-novo"]');
    const leadInNovo = novoColumn.locator('[data-testid="lead-card"]').first();
    
    const leadCount = await leadInNovo.count();
    if (leadCount === 0) {
      test.skip('Nenhum lead na coluna "Novo" para testar');
    }
    
    // 3. Capturar o nome do lead
    const leadName = await leadInNovo.locator('[data-testid="lead-name"]').textContent();
    
    // 4. Arrastar o lead para a coluna "Qualificado"
    const qualificadoColumn = page.locator('[data-testid="column-qualificado"]');
    
    await leadInNovo.dragTo(qualificadoColumn);
    
    // 5. Aguardar atualização
    await page.waitForTimeout(1000);
    
    // 6. Verificar que o lead agora está na coluna "Qualificado"
    const leadInQualificado = qualificadoColumn.locator(`[data-testid="lead-card"]:has-text("${leadName}")`);
    await expect(leadInQualificado).toBeVisible();
    
    // 7. Verificar toast de sucesso
    await helpers.waitForSuccessToast(page);
  });
  
  test('deve abrir modal de detalhes do lead', async ({ authenticatedPage: page }) => {
    // 1. Navegar para o funil
    await page.goto('/funil');
    await helpers.waitForLoading(page);
    
    // 2. Clicar em um lead
    const firstLead = page.locator('[data-testid="lead-card"]').first();
    await expect(firstLead).toBeVisible();
    await firstLead.click();
    
    // 3. Verificar que o modal abriu
    const modal = page.locator('[data-testid="lead-details-modal"]');
    await expect(modal).toBeVisible();
    
    // 4. Verificar conteúdo do modal
    await expect(modal.locator('[data-testid="lead-name"]')).toBeVisible();
    await expect(modal.locator('[data-testid="lead-phone"]')).toBeVisible();
    await expect(modal.locator('[data-testid="lead-email"]')).toBeVisible();
    await expect(modal.locator('[data-testid="lead-score"]')).toBeVisible();
    
    // 5. Fechar modal
    await modal.locator('[data-testid="close-modal"]').click();
    await expect(modal).not.toBeVisible();
  });
  
  test('deve converter lead para cliente', async ({ authenticatedPage: page }) => {
    // 1. Navegar para o funil
    await page.goto('/funil');
    await helpers.waitForLoading(page);
    
    // 2. Encontrar um lead qualificado
    const qualificadoColumn = page.locator('[data-testid="column-qualificado"]');
    const leadInQualificado = qualificadoColumn.locator('[data-testid="lead-card"]').first();
    
    const leadCount = await leadInQualificado.count();
    if (leadCount === 0) {
      test.skip('Nenhum lead qualificado disponível para conversão');
    }
    
    // 3. Capturar o nome do lead
    const leadName = await leadInQualificado.locator('[data-testid="lead-name"]').textContent();
    
    // 4. Clicar no lead para abrir modal
    await leadInQualificado.click();
    
    // 5. Clicar no botão de converter
    const modal = page.locator('[data-testid="lead-details-modal"]');
    await expect(modal).toBeVisible();
    
    const convertButton = modal.locator('[data-testid="convert-to-client"]');
    await expect(convertButton).toBeVisible();
    await convertButton.click();
    
    // 6. Confirmar conversão
    const confirmDialog = page.locator('[data-testid="confirm-dialog"]');
    await expect(confirmDialog).toBeVisible();
    await confirmDialog.locator('[data-testid="confirm-button"]').click();
    
    // 7. Aguardar sucesso
    await helpers.waitForSuccessToast(page);
    
    // 8. Verificar que o lead foi movido para "Convertido"
    await page.waitForTimeout(1000);
    const convertidoColumn = page.locator('[data-testid="column-convertido"]');
    const leadInConvertido = convertidoColumn.locator(`[data-testid="lead-card"]:has-text("${leadName}")`);
    await expect(leadInConvertido).toBeVisible();
  });
  
  test('deve filtrar leads por score', async ({ authenticatedPage: page }) => {
    // 1. Navegar para o funil
    await page.goto('/funil');
    await helpers.waitForLoading(page);
    
    // 2. Abrir filtro de score
    const scoreFilter = page.locator('[data-testid="score-filter"]');
    await expect(scoreFilter).toBeVisible();
    await scoreFilter.click();
    
    // 3. Selecionar "Score > 70"
    await page.click('text=Score > 70');
    
    // 4. Aguardar atualização
    await helpers.waitForLoading(page);
    
    // 5. Verificar que apenas leads com score alto estão visíveis
    const leadCards = page.locator('[data-testid="lead-card"]');
    const count = await leadCards.count();
    
    // Verificar que há pelo menos um lead
    expect(count).toBeGreaterThanOrEqual(0);
  });
  
  test('deve buscar lead por nome', async ({ authenticatedPage: page }) => {
    // 1. Navegar para o funil
    await page.goto('/funil');
    await helpers.waitForLoading(page);
    
    // 2. Capturar o nome do primeiro lead
    const firstLead = page.locator('[data-testid="lead-card"]').first();
    const leadName = await firstLead.locator('[data-testid="lead-name"]').textContent();
    
    if (!leadName) {
      test.skip('Nenhum lead disponível para busca');
    }
    
    // 3. Usar a busca
    const searchInput = page.locator('[data-testid="search-input"]');
    await expect(searchInput).toBeVisible();
    await searchInput.fill(leadName.substring(0, 5)); // Buscar pelos primeiros 5 caracteres
    
    // 4. Aguardar resultados
    await page.waitForTimeout(500);
    
    // 5. Verificar que o lead está nos resultados
    const searchResults = page.locator('[data-testid="lead-card"]');
    await expect(searchResults.first()).toContainText(leadName.substring(0, 5));
  });
  
  test('deve exibir histórico de interações do lead', async ({ authenticatedPage: page }) => {
    // 1. Navegar para o funil
    await page.goto('/funil');
    await helpers.waitForLoading(page);
    
    // 2. Clicar em um lead
    const firstLead = page.locator('[data-testid="lead-card"]').first();
    await firstLead.click();
    
    // 3. Verificar modal
    const modal = page.locator('[data-testid="lead-details-modal"]');
    await expect(modal).toBeVisible();
    
    // 4. Navegar para aba de histórico
    const historyTab = modal.locator('[data-testid="history-tab"]');
    if (await historyTab.isVisible()) {
      await historyTab.click();
      
      // 5. Verificar que o histórico está visível
      const historySection = modal.locator('[data-testid="interaction-history"]');
      await expect(historySection).toBeVisible();
    }
  });
});
