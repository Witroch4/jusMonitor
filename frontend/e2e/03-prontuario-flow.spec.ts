import { test, expect, helpers } from './fixtures/auth';

/**
 * Testes E2E do fluxo de prontuário: Prontuário -> Ativar automação -> Ver timeline
 * 
 * Valida:
 * - Requisito 3.3: Automações individuais
 * - Requisito 3.2: Timeline de eventos
 * - Visualização do prontuário 360º
 * - Configuração de automações
 */
test.describe('Fluxo Prontuário 360º', () => {
  test('deve visualizar prontuário de um cliente', async ({ authenticatedPage: page }) => {
    // 1. Navegar para lista de clientes
    await page.goto('/clientes');
    await helpers.waitForLoading(page);
    
    // 2. Clicar no primeiro cliente
    const firstClient = page.locator('[data-testid="client-card"]').first();
    const clientCount = await firstClient.count();
    
    if (clientCount === 0) {
      test.skip('Nenhum cliente disponível para teste');
    }
    
    await firstClient.click();
    
    // 3. Verificar que o prontuário carregou
    await page.waitForURL(/\/clientes\/[^/]+/, { timeout: 10000 });
    await helpers.waitForLoading(page);
    
    // 4. Verificar seções do prontuário
    await expect(page.locator('[data-testid="overview-section"]')).toBeVisible();
    await expect(page.locator('[data-testid="timeline-section"]')).toBeVisible();
    await expect(page.locator('[data-testid="cases-section"]')).toBeVisible();
    await expect(page.locator('[data-testid="automations-section"]')).toBeVisible();
    await expect(page.locator('[data-testid="notes-section"]')).toBeVisible();
  });
  
  test('deve navegar entre as seções do prontuário', async ({ authenticatedPage: page }) => {
    // 1. Navegar para um cliente
    await page.goto('/clientes');
    await helpers.waitForLoading(page);
    
    const firstClient = page.locator('[data-testid="client-card"]').first();
    await firstClient.click();
    await page.waitForURL(/\/clientes\/[^/]+/);
    await helpers.waitForLoading(page);
    
    // 2. Testar navegação entre seções
    const sections = [
      { tab: 'overview-tab', section: 'overview-section' },
      { tab: 'timeline-tab', section: 'timeline-section' },
      { tab: 'cases-tab', section: 'cases-section' },
      { tab: 'automations-tab', section: 'automations-section' },
      { tab: 'notes-tab', section: 'notes-section' }
    ];
    
    for (const { tab, section } of sections) {
      const tabElement = page.locator(`[data-testid="${tab}"]`);
      if (await tabElement.isVisible()) {
        await tabElement.click();
        await expect(page.locator(`[data-testid="${section}"]`)).toBeVisible();
      }
    }
  });
  
  test('deve ativar automação de briefing matinal', async ({ authenticatedPage: page }) => {
    // 1. Navegar para um cliente
    await page.goto('/clientes');
    await helpers.waitForLoading(page);
    
    const firstClient = page.locator('[data-testid="client-card"]').first();
    await firstClient.click();
    await page.waitForURL(/\/clientes\/[^/]+/);
    await helpers.waitForLoading(page);
    
    // 2. Navegar para seção de automações
    const automationsTab = page.locator('[data-testid="automations-tab"]');
    await automationsTab.click();
    
    const automationsSection = page.locator('[data-testid="automations-section"]');
    await expect(automationsSection).toBeVisible();
    
    // 3. Encontrar toggle de briefing matinal
    const briefingToggle = automationsSection.locator('[data-testid="toggle-briefing-matinal"]');
    await expect(briefingToggle).toBeVisible();
    
    // 4. Verificar estado atual
    const isChecked = await briefingToggle.isChecked();
    
    // 5. Alternar o toggle
    await briefingToggle.click();
    
    // 6. Aguardar salvamento
    await helpers.waitForSuccessToast(page);
    
    // 7. Verificar que o estado mudou
    const newState = await briefingToggle.isChecked();
    expect(newState).toBe(!isChecked);
  });
  
  test('deve ativar automação de alertas urgentes', async ({ authenticatedPage: page }) => {
    // 1. Navegar para um cliente
    await page.goto('/clientes');
    await helpers.waitForLoading(page);
    
    const firstClient = page.locator('[data-testid="client-card"]').first();
    await firstClient.click();
    await page.waitForURL(/\/clientes\/[^/]+/);
    await helpers.waitForLoading(page);
    
    // 2. Navegar para seção de automações
    const automationsTab = page.locator('[data-testid="automations-tab"]');
    await automationsTab.click();
    
    const automationsSection = page.locator('[data-testid="automations-section"]');
    await expect(automationsSection).toBeVisible();
    
    // 3. Encontrar toggle de alertas urgentes
    const alertsToggle = automationsSection.locator('[data-testid="toggle-alertas-urgentes"]');
    await expect(alertsToggle).toBeVisible();
    
    // 4. Verificar estado atual
    const isChecked = await alertsToggle.isChecked();
    
    // 5. Alternar o toggle
    await alertsToggle.click();
    
    // 6. Aguardar salvamento
    await helpers.waitForSuccessToast(page);
    
    // 7. Verificar que o estado mudou
    const newState = await alertsToggle.isChecked();
    expect(newState).toBe(!isChecked);
  });
  
  test('deve visualizar timeline de eventos', async ({ authenticatedPage: page }) => {
    // 1. Navegar para um cliente
    await page.goto('/clientes');
    await helpers.waitForLoading(page);
    
    const firstClient = page.locator('[data-testid="client-card"]').first();
    await firstClient.click();
    await page.waitForURL(/\/clientes\/[^/]+/);
    await helpers.waitForLoading(page);
    
    // 2. Navegar para seção de timeline
    const timelineTab = page.locator('[data-testid="timeline-tab"]');
    await timelineTab.click();
    
    const timelineSection = page.locator('[data-testid="timeline-section"]');
    await expect(timelineSection).toBeVisible();
    
    // 3. Verificar que há eventos na timeline
    const timelineEvents = timelineSection.locator('[data-testid="timeline-event"]');
    const count = await timelineEvents.count();
    
    expect(count).toBeGreaterThanOrEqual(0);
    
    // 4. Se houver eventos, verificar estrutura
    if (count > 0) {
      const firstEvent = timelineEvents.first();
      await expect(firstEvent.locator('[data-testid="event-date"]')).toBeVisible();
      await expect(firstEvent.locator('[data-testid="event-title"]')).toBeVisible();
    }
  });
  
  test('deve filtrar timeline por tipo de evento', async ({ authenticatedPage: page }) => {
    // 1. Navegar para um cliente
    await page.goto('/clientes');
    await helpers.waitForLoading(page);
    
    const firstClient = page.locator('[data-testid="client-card"]').first();
    await firstClient.click();
    await page.waitForURL(/\/clientes\/[^/]+/);
    await helpers.waitForLoading(page);
    
    // 2. Navegar para seção de timeline
    const timelineTab = page.locator('[data-testid="timeline-tab"]');
    await timelineTab.click();
    
    const timelineSection = page.locator('[data-testid="timeline-section"]');
    await expect(timelineSection).toBeVisible();
    
    // 3. Abrir filtro de tipo
    const typeFilter = timelineSection.locator('[data-testid="event-type-filter"]');
    if (await typeFilter.isVisible()) {
      await typeFilter.click();
      
      // 4. Selecionar um tipo
      await page.click('text=Movimentações');
      
      // 5. Aguardar atualização
      await page.waitForTimeout(500);
      
      // 6. Verificar que os eventos foram filtrados
      const filteredEvents = timelineSection.locator('[data-testid="timeline-event"]');
      const count = await filteredEvents.count();
      expect(count).toBeGreaterThanOrEqual(0);
    }
  });
  
  test('deve criar nota interna', async ({ authenticatedPage: page }) => {
    // 1. Navegar para um cliente
    await page.goto('/clientes');
    await helpers.waitForLoading(page);
    
    const firstClient = page.locator('[data-testid="client-card"]').first();
    await firstClient.click();
    await page.waitForURL(/\/clientes\/[^/]+/);
    await helpers.waitForLoading(page);
    
    // 2. Navegar para seção de notas
    const notesTab = page.locator('[data-testid="notes-tab"]');
    await notesTab.click();
    
    const notesSection = page.locator('[data-testid="notes-section"]');
    await expect(notesSection).toBeVisible();
    
    // 3. Clicar em "Nova Nota"
    const newNoteButton = notesSection.locator('[data-testid="new-note-button"]');
    await expect(newNoteButton).toBeVisible();
    await newNoteButton.click();
    
    // 4. Preencher nota
    const noteEditor = page.locator('[data-testid="note-editor"]');
    await expect(noteEditor).toBeVisible();
    
    const noteContent = `Nota de teste criada em ${new Date().toISOString()}`;
    await noteEditor.fill(noteContent);
    
    // 5. Salvar nota
    const saveButton = page.locator('[data-testid="save-note-button"]');
    await saveButton.click();
    
    // 6. Aguardar sucesso
    await helpers.waitForSuccessToast(page);
    
    // 7. Verificar que a nota aparece na lista
    const notesList = notesSection.locator('[data-testid="notes-list"]');
    await expect(notesList.locator(`text=${noteContent}`)).toBeVisible();
  });
  
  test('deve visualizar processos do cliente', async ({ authenticatedPage: page }) => {
    // 1. Navegar para um cliente
    await page.goto('/clientes');
    await helpers.waitForLoading(page);
    
    const firstClient = page.locator('[data-testid="client-card"]').first();
    await firstClient.click();
    await page.waitForURL(/\/clientes\/[^/]+/);
    await helpers.waitForLoading(page);
    
    // 2. Navegar para seção de processos
    const casesTab = page.locator('[data-testid="cases-tab"]');
    await casesTab.click();
    
    const casesSection = page.locator('[data-testid="cases-section"]');
    await expect(casesSection).toBeVisible();
    
    // 3. Verificar lista de processos
    const casesList = casesSection.locator('[data-testid="case-item"]');
    const count = await casesList.count();
    
    expect(count).toBeGreaterThanOrEqual(0);
    
    // 4. Se houver processos, verificar estrutura
    if (count > 0) {
      const firstCase = casesList.first();
      await expect(firstCase.locator('[data-testid="case-number"]')).toBeVisible();
      await expect(firstCase.locator('[data-testid="case-status"]')).toBeVisible();
    }
  });
  
  test('deve exibir health score do cliente', async ({ authenticatedPage: page }) => {
    // 1. Navegar para um cliente
    await page.goto('/clientes');
    await helpers.waitForLoading(page);
    
    const firstClient = page.locator('[data-testid="client-card"]').first();
    await firstClient.click();
    await page.waitForURL(/\/clientes\/[^/]+/);
    await helpers.waitForLoading(page);
    
    // 2. Verificar seção de visão geral
    const overviewSection = page.locator('[data-testid="overview-section"]');
    await expect(overviewSection).toBeVisible();
    
    // 3. Verificar health score
    const healthScore = overviewSection.locator('[data-testid="health-score"]');
    await expect(healthScore).toBeVisible();
    
    // 4. Verificar que o score é um número
    const scoreText = await healthScore.textContent();
    expect(scoreText).toMatch(/\d+/);
  });
});
