import { defineConfig, devices } from '@playwright/test';

/**
 * Configuração do Playwright para testes E2E do JusMonitor
 * 
 * @see https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  testDir: './e2e',
  
  /* Global setup */
  globalSetup: require.resolve('./e2e/global-setup'),
  
  /* Timeout máximo por teste */
  timeout: 30 * 1000,
  
  /* Configuração de expect */
  expect: {
    timeout: 5000
  },
  
  /* Executar testes em paralelo */
  fullyParallel: true,
  
  /* Falhar build no CI se testes foram commitados com .only */
  forbidOnly: !!process.env.CI,
  
  /* Retry em caso de falha no CI */
  retries: process.env.CI ? 2 : 0,
  
  /* Workers para execução paralela */
  workers: process.env.CI ? 1 : undefined,
  
  /* Reporter */
  reporter: [
    ['html'],
    ['list']
  ],
  
  /* Configuração compartilhada para todos os projetos */
  use: {
    /* URL base para navegação */
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3000',
    
    /* Coletar trace em caso de falha */
    trace: 'on-first-retry',
    
    /* Screenshot em caso de falha */
    screenshot: 'only-on-failure',
    
    /* Video em caso de falha */
    video: 'retain-on-failure',
  },

  /* Configurar projetos para diferentes browsers */
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },

    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },

    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },

    /* Testes mobile */
    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'] },
    },
    {
      name: 'Mobile Safari',
      use: { ...devices['iPhone 12'] },
    },
  ],

  /* Servidor de desenvolvimento */
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000,
  },
});
