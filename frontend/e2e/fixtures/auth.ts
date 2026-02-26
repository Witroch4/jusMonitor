import { test as base, expect } from '@playwright/test';
import type { Page } from '@playwright/test';

/**
 * Tipos para fixtures customizadas
 */
type AuthFixtures = {
  authenticatedPage: Page;
  adminPage: Page;
  lawyerPage: Page;
};

/**
 * Credenciais de teste
 */
const TEST_USERS = {
  admin: {
    email: 'admin@demo.com',
    password: 'admin123',
    role: 'admin'
  },
  lawyer: {
    email: 'advogado@demo.com',
    password: 'lawyer123',
    role: 'advogado'
  },
  assistant: {
    email: 'assistente@demo.com',
    password: 'assistant123',
    role: 'assistente'
  }
};

/**
 * Função auxiliar para fazer login
 */
async function login(page: Page, email: string, password: string) {
  await page.goto('/login');
  
  // Preencher formulário de login
  await page.fill('input[name="email"]', email);
  await page.fill('input[name="password"]', password);
  
  // Clicar no botão de login
  await page.click('button[type="submit"]');
  
  // Aguardar redirecionamento para dashboard
  await page.waitForURL('/dashboard', { timeout: 10000 });
  
  // Verificar que o login foi bem-sucedido
  await expect(page).toHaveURL('/dashboard');
}

/**
 * Fixture para página autenticada com usuário padrão (advogado)
 */
export const test = base.extend<AuthFixtures>({
  authenticatedPage: async ({ browser }, use) => {
    const context = await browser.newContext();
    const page = await context.newPage();
    
    await login(page, TEST_USERS.lawyer.email, TEST_USERS.lawyer.password);
    
    await use(page);
    
    await context.close();
  },
  
  adminPage: async ({ browser }, use) => {
    const context = await browser.newContext();
    const page = await context.newPage();
    
    await login(page, TEST_USERS.admin.email, TEST_USERS.admin.password);
    
    await use(page);
    
    await context.close();
  },
  
  lawyerPage: async ({ browser }, use) => {
    const context = await browser.newContext();
    const page = await context.newPage();
    
    await login(page, TEST_USERS.lawyer.email, TEST_USERS.lawyer.password);
    
    await use(page);
    
    await context.close();
  },
});

export { expect } from '@playwright/test';

/**
 * Helpers para testes
 */
export const helpers = {
  /**
   * Aguardar que o loading desapareça
   */
  async waitForLoading(page: Page) {
    await page.waitForSelector('[data-testid="loading"]', { state: 'hidden', timeout: 10000 });
  },
  
  /**
   * Aguardar toast de sucesso
   */
  async waitForSuccessToast(page: Page) {
    await page.waitForSelector('[data-testid="toast-success"]', { timeout: 5000 });
  },
  
  /**
   * Aguardar toast de erro
   */
  async waitForErrorToast(page: Page) {
    await page.waitForSelector('[data-testid="toast-error"]', { timeout: 5000 });
  },
  
  /**
   * Fazer logout
   */
  async logout(page: Page) {
    await page.click('[data-testid="user-menu"]');
    await page.click('[data-testid="logout-button"]');
    await page.waitForURL('/login');
  }
};
