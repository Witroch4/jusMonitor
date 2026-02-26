import { test, expect, helpers } from './fixtures/auth';

/**
 * Testes E2E do fluxo principal: Login -> Dashboard -> Ver caso urgente
 * 
 * Valida:
 * - Requisito 4.1: Dashboard/Central Operacional
 * - Login e autenticação
 * - Visualização de casos urgentes
 * - Navegação para prontuário
 */
test.describe('Fluxo Dashboard', () => {
  test('deve fazer login e visualizar dashboard com casos urgentes', async ({ page }) => {
    // 1. Fazer login
    await page.goto('/login');
    await page.fill('input[name="email"]', 'advogado@demo.com');
    await page.fill('input[name="password"]', 'lawyer123');
    await page.click('button[type="submit"]');
    
    // 2. Verificar redirecionamento para dashboard
    await page.waitForURL('/dashboard', { timeout: 10000 });
    await expect(page).toHaveURL('/dashboard');
    
    // 3. Verificar que o dashboard carregou
    await expect(page.locator('h1')).toContainText('Central Operacional');
    
    // 4. Aguardar carregamento dos dados
    await helpers.waitForLoading(page);
    
    // 5. Verificar que os blocos do dashboard estão visíveis
    await expect(page.locator('[data-testid="urgent-cases"]')).toBeVisible();
    await expect(page.locator('[data-testid="attention-cases"]')).toBeVisible();
    await expect(page.locator('[data-testid="good-news"]')).toBeVisible();
    await expect(page.locator('[data-testid="noise"]')).toBeVisible();
    await expect(page.locator('[data-testid="metrics"]')).toBeVisible();
  });
  
  test('deve visualizar detalhes de um caso urgente', async ({ authenticatedPage: page }) => {
    // 1. Navegar para dashboard
    await page.goto('/dashboard');
    await helpers.waitForLoading(page);
    
    // 2. Verificar se há casos urgentes
    const urgentCases = page.locator('[data-testid="urgent-cases"] [data-testid="case-card"]');
    const count = await urgentCases.count();
    
    if (count === 0) {
      test.skip('Nenhum caso urgente disponível para teste');
    }
    
    // 3. Clicar no primeiro caso urgente
    const firstCase = urgentCases.first();
    await expect(firstCase).toBeVisible();
    
    // Capturar o número do processo antes de clicar
    const caseNumber = await firstCase.locator('[data-testid="case-number"]').textContent();
    
    await firstCase.click();
    
    // 4. Verificar redirecionamento para prontuário
    await page.waitForURL(/\/clientes\/[^/]+/, { timeout: 10000 });
    
    // 5. Verificar que o prontuário carregou
    await expect(page.locator('h1')).toBeVisible();
    await helpers.waitForLoading(page);
    
    // 6. Verificar que o número do processo está visível
    if (caseNumber) {
      await expect(page.locator('text=' + caseNumber)).toBeVisible();
    }
  });
  
  test('deve filtrar casos por período', async ({ authenticatedPage: page }) => {
    // 1. Navegar para dashboard
    await page.goto('/dashboard');
    await helpers.waitForLoading(page);
    
    // 2. Abrir filtro de período
    const periodFilter = page.locator('[data-testid="period-filter"]');
    await expect(periodFilter).toBeVisible();
    await periodFilter.click();
    
    // 3. Selecionar "Últimos 7 dias"
    await page.click('text=Últimos 7 dias');
    
    // 4. Aguardar atualização dos dados
    await helpers.waitForLoading(page);
    
    // 5. Verificar que os dados foram atualizados
    await expect(page.locator('[data-testid="urgent-cases"]')).toBeVisible();
  });
  
  test('deve exibir métricas do escritório', async ({ authenticatedPage: page }) => {
    // 1. Navegar para dashboard
    await page.goto('/dashboard');
    await helpers.waitForLoading(page);
    
    // 2. Verificar que as métricas estão visíveis
    const metricsSection = page.locator('[data-testid="metrics"]');
    await expect(metricsSection).toBeVisible();
    
    // 3. Verificar métricas específicas
    await expect(metricsSection.locator('[data-testid="conversion-rate"]')).toBeVisible();
    await expect(metricsSection.locator('[data-testid="response-time"]')).toBeVisible();
    await expect(metricsSection.locator('[data-testid="satisfaction"]')).toBeVisible();
  });
  
  test('deve navegar entre os blocos do dashboard', async ({ authenticatedPage: page }) => {
    // 1. Navegar para dashboard
    await page.goto('/dashboard');
    await helpers.waitForLoading(page);
    
    // 2. Verificar navegação para cada bloco
    const blocks = [
      { testId: 'urgent-cases', title: 'Urgente' },
      { testId: 'attention-cases', title: 'Atenção' },
      { testId: 'good-news', title: 'Boas Notícias' },
      { testId: 'noise', title: 'Ruído' }
    ];
    
    for (const block of blocks) {
      const blockElement = page.locator(`[data-testid="${block.testId}"]`);
      await expect(blockElement).toBeVisible();
      
      // Verificar que o título está presente
      await expect(blockElement.locator(`text=${block.title}`)).toBeVisible();
    }
  });
});
