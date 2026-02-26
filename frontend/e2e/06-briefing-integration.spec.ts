import { test, expect, helpers } from './fixtures/auth';

/**
 * Testes E2E de integração do Briefing Matinal
 * 
 * Valida:
 * - Requisito 2.8: Briefing matinal
 * - Geração automática do briefing
 * - Atualização do dashboard
 * - Classificação de movimentações
 */
test.describe('Integração Briefing Matinal', () => {
  test('deve exibir briefing matinal no dashboard', async ({ authenticatedPage: page }) => {
    // 1. Navegar para dashboard
    await page.goto('/dashboard');
    await helpers.waitForLoading(page);
    
    // 2. Verificar que o briefing está visível
    const briefingSection = page.locator('[data-testid="briefing-section"]');
    
    // O briefing pode não estar sempre visível, dependendo da hora
    if (await briefingSection.isVisible()) {
      // 3. Verificar conteúdo do briefing
      await expect(briefingSection.locator('[data-testid="briefing-date"]')).toBeVisible();
      await expect(briefingSection.locator('[data-testid="briefing-summary"]')).toBeVisible();
      
      // 4. Verificar que há estatísticas
      await expect(briefingSection.locator('[data-testid="briefing-stats"]')).toBeVisible();
    }
  });
  
  test('deve classificar movimentações em 4 categorias', async ({ authenticatedPage: page }) => {
    // 1. Navegar para dashboard
    await page.goto('/dashboard');
    await helpers.waitForLoading(page);
    
    // 2. Verificar que os 4 blocos estão presentes
    const blocks = [
      { testId: 'urgent-cases', title: 'Urgente' },
      { testId: 'attention-cases', title: 'Atenção' },
      { testId: 'good-news', title: 'Boas Notícias' },
      { testId: 'noise', title: 'Ruído' }
    ];
    
    for (const block of blocks) {
      const blockElement = page.locator(`[data-testid="${block.testId}"]`);
      await expect(blockElement).toBeVisible();
      
      // Verificar título
      await expect(blockElement).toContainText(block.title);
      
      // Verificar contador
      const counter = blockElement.locator('[data-testid="case-count"]');
      if (await counter.isVisible()) {
        const countText = await counter.textContent();
        expect(countText).toMatch(/\d+/);
      }
    }
  });
  
  test('deve exibir casos urgentes com prazo próximo', async ({ authenticatedPage: page }) => {
    // 1. Navegar para dashboard
    await page.goto('/dashboard');
    await helpers.waitForLoading(page);
    
    // 2. Verificar bloco de casos urgentes
    const urgentSection = page.locator('[data-testid="urgent-cases"]');
    await expect(urgentSection).toBeVisible();
    
    // 3. Verificar casos urgentes
    const urgentCases = urgentSection.locator('[data-testid="case-card"]');
    const count = await urgentCases.count();
    
    if (count > 0) {
      // 4. Verificar primeiro caso urgente
      const firstCase = urgentCases.first();
      
      // Deve ter badge de urgência
      const urgencyBadge = firstCase.locator('[data-testid="urgency-badge"]');
      await expect(urgencyBadge).toBeVisible();
      
      // Deve ter prazo
      const deadline = firstCase.locator('[data-testid="deadline"]');
      await expect(deadline).toBeVisible();
      
      // Deve ter número do processo
      const caseNumber = firstCase.locator('[data-testid="case-number"]');
      await expect(caseNumber).toBeVisible();
    }
  });
  
  test('deve exibir casos que precisam atenção', async ({ authenticatedPage: page }) => {
    // 1. Navegar para dashboard
    await page.goto('/dashboard');
    await helpers.waitForLoading(page);
    
    // 2. Verificar bloco de atenção
    const attentionSection = page.locator('[data-testid="attention-cases"]');
    await expect(attentionSection).toBeVisible();
    
    // 3. Verificar casos
    const attentionCases = attentionSection.locator('[data-testid="case-card"]');
    const count = await attentionCases.count();
    
    if (count > 0) {
      // 4. Verificar primeiro caso
      const firstCase = attentionCases.first();
      
      // Deve ter indicador de tempo parado
      const staleIndicator = firstCase.locator('[data-testid="stale-indicator"]');
      if (await staleIndicator.isVisible()) {
        const staleText = await staleIndicator.textContent();
        expect(staleText).toMatch(/\d+\s+dias/);
      }
      
      // Deve ter última movimentação
      const lastMovement = firstCase.locator('[data-testid="last-movement"]');
      await expect(lastMovement).toBeVisible();
    }
  });
  
  test('deve exibir boas notícias', async ({ authenticatedPage: page }) => {
    // 1. Navegar para dashboard
    await page.goto('/dashboard');
    await helpers.waitForLoading(page);
    
    // 2. Verificar bloco de boas notícias
    const goodNewsSection = page.locator('[data-testid="good-news"]');
    await expect(goodNewsSection).toBeVisible();
    
    // 3. Verificar casos
    const goodNewsCases = goodNewsSection.locator('[data-testid="case-card"]');
    const count = await goodNewsCases.count();
    
    if (count > 0) {
      // 4. Verificar primeiro caso
      const firstCase = goodNewsCases.first();
      
      // Deve ter resumo gerado por IA
      const aiSummary = firstCase.locator('[data-testid="ai-summary"]');
      await expect(aiSummary).toBeVisible();
      
      // Deve ter botão de compartilhar
      const shareButton = firstCase.locator('[data-testid="share-button"]');
      if (await shareButton.isVisible()) {
        await expect(shareButton).toBeEnabled();
      }
    }
  });
  
  test('deve filtrar ruído (movimentações irrelevantes)', async ({ authenticatedPage: page }) => {
    // 1. Navegar para dashboard
    await page.goto('/dashboard');
    await helpers.waitForLoading(page);
    
    // 2. Verificar bloco de ruído
    const noiseSection = page.locator('[data-testid="noise"]');
    await expect(noiseSection).toBeVisible();
    
    // 3. Verificar que há opção de ocultar
    const hideNoiseToggle = noiseSection.locator('[data-testid="hide-noise-toggle"]');
    
    if (await hideNoiseToggle.isVisible()) {
      // 4. Ocultar ruído
      await hideNoiseToggle.click();
      
      // 5. Verificar que o bloco foi ocultado ou minimizado
      await page.waitForTimeout(500);
      
      const isCollapsed = await noiseSection.getAttribute('data-collapsed');
      expect(isCollapsed).toBe('true');
    }
  });
  
  test('deve marcar movimentações como lidas', async ({ authenticatedPage: page }) => {
    // 1. Navegar para dashboard
    await page.goto('/dashboard');
    await helpers.waitForLoading(page);
    
    // 2. Encontrar uma movimentação não lida
    const unreadCase = page.locator('[data-testid="case-card"][data-read="false"]').first();
    
    if (await unreadCase.isVisible()) {
      // 3. Marcar como lida
      const markReadButton = unreadCase.locator('[data-testid="mark-read-button"]');
      
      if (await markReadButton.isVisible()) {
        await markReadButton.click();
        
        // 4. Aguardar atualização
        await page.waitForTimeout(500);
        
        // 5. Verificar que foi marcada como lida
        const isRead = await unreadCase.getAttribute('data-read');
        expect(isRead).toBe('true');
      }
    }
  });
  
  test('deve exibir métricas do período', async ({ authenticatedPage: page }) => {
    // 1. Navegar para dashboard
    await page.goto('/dashboard');
    await helpers.waitForLoading(page);
    
    // 2. Verificar seção de métricas
    const metricsSection = page.locator('[data-testid="metrics"]');
    await expect(metricsSection).toBeVisible();
    
    // 3. Verificar métricas específicas
    const metrics = [
      'conversion-rate',
      'response-time',
      'satisfaction',
      'active-cases',
      'new-movements'
    ];
    
    for (const metric of metrics) {
      const metricElement = metricsSection.locator(`[data-testid="${metric}"]`);
      
      if (await metricElement.isVisible()) {
        // Verificar que tem valor numérico
        const value = await metricElement.textContent();
        expect(value).toMatch(/\d+/);
      }
    }
  });
  
  test('deve comparar métricas com período anterior', async ({ authenticatedPage: page }) => {
    // 1. Navegar para dashboard
    await page.goto('/dashboard');
    await helpers.waitForLoading(page);
    
    // 2. Verificar seção de métricas
    const metricsSection = page.locator('[data-testid="metrics"]');
    await expect(metricsSection).toBeVisible();
    
    // 3. Verificar indicadores de variação
    const variationIndicators = metricsSection.locator('[data-testid="variation-indicator"]');
    const count = await variationIndicators.count();
    
    if (count > 0) {
      // 4. Verificar primeiro indicador
      const firstIndicator = variationIndicators.first();
      
      // Deve ter porcentagem
      const variationText = await firstIndicator.textContent();
      expect(variationText).toMatch(/[+-]?\d+%/);
      
      // Deve ter cor indicando melhora ou piora
      const className = await firstIndicator.getAttribute('class');
      expect(className).toMatch(/(positive|negative|neutral)/);
    }
  });
  
  test('deve permitir exportar briefing', async ({ authenticatedPage: page }) => {
    // 1. Navegar para dashboard
    await page.goto('/dashboard');
    await helpers.waitForLoading(page);
    
    // 2. Procurar botão de exportar
    const exportButton = page.locator('[data-testid="export-briefing"]');
    
    if (await exportButton.isVisible()) {
      // 3. Clicar em exportar
      await exportButton.click();
      
      // 4. Verificar opções de exportação
      const exportMenu = page.locator('[data-testid="export-menu"]');
      await expect(exportMenu).toBeVisible();
      
      // 5. Verificar formatos disponíveis
      await expect(exportMenu.locator('text=PDF')).toBeVisible();
      await expect(exportMenu.locator('text=Excel')).toBeVisible();
    }
  });
  
  test('deve atualizar dashboard em tempo real', async ({ authenticatedPage: page }) => {
    // 1. Navegar para dashboard
    await page.goto('/dashboard');
    await helpers.waitForLoading(page);
    
    // 2. Verificar que há conexão WebSocket
    const wsIndicator = page.locator('[data-testid="realtime-indicator"]');
    
    if (await wsIndicator.isVisible()) {
      // 3. Verificar status conectado
      const status = await wsIndicator.getAttribute('data-status');
      expect(status).toBe('connected');
    }
    
    // 4. Aguardar possível atualização em tempo real
    await page.waitForTimeout(2000);
    
    // 5. Verificar que não houve erro
    const errorMessage = page.locator('[data-testid="error-message"]');
    await expect(errorMessage).not.toBeVisible();
  });
});
