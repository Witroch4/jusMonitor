import { test, expect, helpers } from './fixtures/auth';

/**
 * Teste de exemplo para demonstrar a estrutura dos testes E2E
 * 
 * Este arquivo serve como referência para criar novos testes.
 * Pode ser deletado em produção.
 */
test.describe('Exemplo de Teste E2E', () => {
  
  /**
   * Teste básico sem autenticação
   */
  test('deve carregar a página de login', async ({ page }) => {
    // 1. Navegar para a página
    await page.goto('/login');
    
    // 2. Verificar que a página carregou
    await expect(page).toHaveURL('/login');
    
    // 3. Verificar elementos da página
    await expect(page.locator('h1')).toContainText('Login');
    await expect(page.locator('input[name="email"]')).toBeVisible();
    await expect(page.locator('input[name="password"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });
  
  /**
   * Teste com autenticação usando fixture
   */
  test('deve acessar dashboard autenticado', async ({ authenticatedPage: page }) => {
    // A página já está autenticada graças à fixture
    
    // 1. Navegar para dashboard
    await page.goto('/dashboard');
    
    // 2. Aguardar carregamento
    await helpers.waitForLoading(page);
    
    // 3. Verificar que está no dashboard
    await expect(page).toHaveURL('/dashboard');
    await expect(page.locator('h1')).toContainText('Central Operacional');
  });
  
  /**
   * Teste com interação de formulário
   */
  test('deve preencher e submeter formulário', async ({ authenticatedPage: page }) => {
    // 1. Navegar para página com formulário
    await page.goto('/clientes/novo');
    await helpers.waitForLoading(page);
    
    // 2. Preencher campos
    await page.fill('input[name="name"]', 'Cliente Teste');
    await page.fill('input[name="email"]', 'cliente@teste.com');
    await page.fill('input[name="phone"]', '11999999999');
    
    // 3. Submeter formulário
    await page.click('button[type="submit"]');
    
    // 4. Aguardar sucesso
    await helpers.waitForSuccessToast(page);
    
    // 5. Verificar redirecionamento
    await page.waitForURL(/\/clientes\/[^/]+/);
  });
  
  /**
   * Teste com seleção de elementos
   */
  test('deve selecionar elementos usando data-testid', async ({ authenticatedPage: page }) => {
    await page.goto('/dashboard');
    await helpers.waitForLoading(page);
    
    // Usar data-testid é a forma recomendada
    const urgentCases = page.locator('[data-testid="urgent-cases"]');
    await expect(urgentCases).toBeVisible();
    
    // Contar elementos
    const caseCards = urgentCases.locator('[data-testid="case-card"]');
    const count = await caseCards.count();
    expect(count).toBeGreaterThanOrEqual(0);
    
    // Selecionar primeiro elemento
    if (count > 0) {
      const firstCard = caseCards.first();
      await expect(firstCard).toBeVisible();
    }
  });
  
  /**
   * Teste com navegação
   */
  test('deve navegar entre páginas', async ({ authenticatedPage: page }) => {
    // 1. Começar no dashboard
    await page.goto('/dashboard');
    await helpers.waitForLoading(page);
    
    // 2. Clicar em link para funil
    await page.click('[data-testid="nav-funil"]');
    
    // 3. Verificar navegação
    await page.waitForURL('/funil');
    await expect(page).toHaveURL('/funil');
    
    // 4. Voltar para dashboard
    await page.click('[data-testid="nav-dashboard"]');
    await page.waitForURL('/dashboard');
  });
  
  /**
   * Teste com modal
   */
  test('deve abrir e fechar modal', async ({ authenticatedPage: page }) => {
    await page.goto('/funil');
    await helpers.waitForLoading(page);
    
    // 1. Clicar em elemento que abre modal
    const firstLead = page.locator('[data-testid="lead-card"]').first();
    
    if (await firstLead.isVisible()) {
      await firstLead.click();
      
      // 2. Verificar que modal abriu
      const modal = page.locator('[data-testid="lead-details-modal"]');
      await expect(modal).toBeVisible();
      
      // 3. Fechar modal
      await modal.locator('[data-testid="close-modal"]').click();
      
      // 4. Verificar que modal fechou
      await expect(modal).not.toBeVisible();
    }
  });
  
  /**
   * Teste com filtros
   */
  test('deve aplicar filtros', async ({ authenticatedPage: page }) => {
    await page.goto('/dashboard');
    await helpers.waitForLoading(page);
    
    // 1. Abrir filtro
    const periodFilter = page.locator('[data-testid="period-filter"]');
    await periodFilter.click();
    
    // 2. Selecionar opção
    await page.click('text=Últimos 7 dias');
    
    // 3. Aguardar atualização
    await helpers.waitForLoading(page);
    
    // 4. Verificar que filtro foi aplicado
    await expect(periodFilter).toContainText('Últimos 7 dias');
  });
  
  /**
   * Teste com verificação condicional
   */
  test('deve lidar com elementos opcionais', async ({ authenticatedPage: page }) => {
    await page.goto('/dashboard');
    await helpers.waitForLoading(page);
    
    // Verificar se elemento existe antes de interagir
    const exportButton = page.locator('[data-testid="export-button"]');
    
    if (await exportButton.isVisible()) {
      await exportButton.click();
      
      const exportMenu = page.locator('[data-testid="export-menu"]');
      await expect(exportMenu).toBeVisible();
    } else {
      // Elemento não está disponível, pular esta parte do teste
      console.log('Botão de exportar não disponível');
    }
  });
  
  /**
   * Teste com espera de condição
   */
  test('deve aguardar condições específicas', async ({ authenticatedPage: page }) => {
    await page.goto('/dashboard');
    
    // Aguardar elemento específico
    await page.waitForSelector('[data-testid="urgent-cases"]', { 
      state: 'visible',
      timeout: 10000 
    });
    
    // Aguardar que elemento desapareça
    await page.waitForSelector('[data-testid="loading"]', { 
      state: 'hidden',
      timeout: 10000 
    });
    
    // Aguardar URL específica
    await page.waitForURL('/dashboard', { timeout: 5000 });
  });
  
  /**
   * Teste com múltiplas asserções
   */
  test('deve validar múltiplos aspectos da página', async ({ authenticatedPage: page }) => {
    await page.goto('/dashboard');
    await helpers.waitForLoading(page);
    
    // Verificar título
    await expect(page.locator('h1')).toContainText('Central Operacional');
    
    // Verificar que seções estão visíveis
    await expect(page.locator('[data-testid="urgent-cases"]')).toBeVisible();
    await expect(page.locator('[data-testid="attention-cases"]')).toBeVisible();
    await expect(page.locator('[data-testid="good-news"]')).toBeVisible();
    await expect(page.locator('[data-testid="noise"]')).toBeVisible();
    
    // Verificar que não há erros
    await expect(page.locator('[data-testid="error-message"]')).not.toBeVisible();
  });
});
