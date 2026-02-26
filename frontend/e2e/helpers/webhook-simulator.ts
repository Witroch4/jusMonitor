import { Page } from '@playwright/test';

/**
 * Helper para simular webhooks de integrações externas
 * 
 * Usado para testar fluxos que dependem de eventos externos:
 * - Chatwit (mensagens, tags)
 * - DataJud (movimentações)
 */

export interface ChatwitWebhookPayload {
  event_type: 'message.received' | 'tag.added' | 'tag.removed';
  timestamp: string;
  contact: {
    id: string;
    name: string;
    phone: string;
    email?: string;
  };
  message?: {
    id: string;
    content: string;
    channel: string;
  };
  tag?: string;
}

export interface DataJudWebhookPayload {
  process_id: string;
  cnj_number: string;
  movements: Array<{
    date: string;
    type: string;
    description: string;
  }>;
}

/**
 * Simula webhook do Chatwit
 */
export async function simulateChatwitWebhook(
  page: Page,
  payload: ChatwitWebhookPayload
): Promise<void> {
  const baseURL = page.context().browser()?.contexts()[0]?.pages()[0]?.url() || 'http://localhost:3000';
  
  // Fazer requisição POST para o endpoint de webhook
  const response = await page.request.post(`${baseURL}/api/webhooks/chatwit`, {
    data: payload,
    headers: {
      'Content-Type': 'application/json',
      // Em produção, incluiria assinatura HMAC
      'X-Chatwit-Signature': 'test-signature'
    }
  });
  
  if (!response.ok()) {
    throw new Error(`Webhook failed: ${response.status()} ${response.statusText()}`);
  }
}

/**
 * Simula polling do DataJud que detecta nova movimentação
 */
export async function simulateDataJudMovement(
  page: Page,
  payload: DataJudWebhookPayload
): Promise<void> {
  const baseURL = page.context().browser()?.contexts()[0]?.pages()[0]?.url() || 'http://localhost:3000';
  
  // Fazer requisição POST para endpoint interno de teste
  const response = await page.request.post(`${baseURL}/api/test/datajud-movement`, {
    data: payload,
    headers: {
      'Content-Type': 'application/json'
    }
  });
  
  if (!response.ok()) {
    throw new Error(`DataJud simulation failed: ${response.status()} ${response.statusText()}`);
  }
}

/**
 * Aguarda processamento assíncrono de webhook
 */
export async function waitForWebhookProcessing(page: Page, timeoutMs: number = 5000): Promise<void> {
  await page.waitForTimeout(timeoutMs);
}

/**
 * Cria payload de mensagem do Chatwit
 */
export function createChatwitMessagePayload(
  contactName: string,
  message: string
): ChatwitWebhookPayload {
  return {
    event_type: 'message.received',
    timestamp: new Date().toISOString(),
    contact: {
      id: `contact-${Date.now()}`,
      name: contactName,
      phone: '+5511999999999',
      email: `${contactName.toLowerCase().replace(/\s/g, '')}@example.com`
    },
    message: {
      id: `msg-${Date.now()}`,
      content: message,
      channel: 'whatsapp'
    }
  };
}

/**
 * Cria payload de tag adicionada no Chatwit
 */
export function createChatwitTagPayload(
  contactId: string,
  tag: string
): ChatwitWebhookPayload {
  return {
    event_type: 'tag.added',
    timestamp: new Date().toISOString(),
    contact: {
      id: contactId,
      name: 'Test Contact',
      phone: '+5511999999999'
    },
    tag
  };
}

/**
 * Cria payload de movimentação do DataJud
 */
export function createDataJudMovementPayload(
  cnjNumber: string,
  movementDescription: string
): DataJudWebhookPayload {
  return {
    process_id: `process-${Date.now()}`,
    cnj_number: cnjNumber,
    movements: [
      {
        date: new Date().toISOString().split('T')[0],
        type: 'Despacho',
        description: movementDescription
      }
    ]
  };
}
