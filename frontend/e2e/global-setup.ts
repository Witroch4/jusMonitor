import { chromium, FullConfig } from '@playwright/test';

/**
 * Global setup executado antes de todos os testes
 * 
 * Usado para:
 * - Verificar se o backend está disponível
 * - Criar dados de seed se necessário
 * - Configurar estado global
 */
async function globalSetup(config: FullConfig) {
  const { baseURL } = config.projects[0].use;
  
  console.log('🚀 Iniciando setup global dos testes E2E...');
  
  // Verificar se o backend está disponível
  const browser = await chromium.launch();
  const page = await browser.newPage();
  
  try {
    // Tentar acessar a página de login
    const response = await page.goto(`${baseURL}/login`, { 
      timeout: 30000,
      waitUntil: 'domcontentloaded'
    });
    
    if (!response || !response.ok()) {
      throw new Error(`Backend não está disponível em ${baseURL}`);
    }
    
    console.log('✅ Backend está disponível');
    
    // Verificar se a API está respondendo
    const apiResponse = await page.request.get(`${baseURL}/api/health`).catch(() => null);
    
    if (apiResponse && apiResponse.ok()) {
      console.log('✅ API está respondendo');
    } else {
      console.warn('⚠️  API health check falhou, mas continuando...');
    }
    
  } catch (error) {
    console.error('❌ Erro no setup global:', error);
    throw error;
  } finally {
    await browser.close();
  }
  
  console.log('✅ Setup global concluído\n');
}

export default globalSetup;
