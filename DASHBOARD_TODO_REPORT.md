# Relatório de Funcionalidades Incompletas do Dashboard

**Data:** 2026-03-08
**Projeto:** JusMonitorIA

---

## Resumo Executivo

Foram identificadas **9 funcionalidades incompletas** no frontend do dashboard, distribuídas em 6 arquivos. As categorias são:

| Categoria | Quantidade |
|-----------|-----------|
| TODO (código não integrado) | 3 |
| "Em Breve" / Coming Soon | 3 |
| Links placeholder (`href="#"`) | 3 |

---

## 1. TODOs no Código

### 1.1 Central de IA — Integração com Agente AI
- **Arquivo:** `frontend/app/(dashboard)/central/page.tsx` — linha 44
- **Comentário:** `// TODO: Integrate with AI agent endpoint`
- **Descrição:** A interface de chat com IA está funcional visualmente, mas as respostas são simuladas com `setTimeout`. Não há integração real com o backend de agentes AI.
- **Impacto:** Alto — funcionalidade principal da Central de IA não funciona.

### 1.2 Conversão de Lead em Cliente
- **Arquivo:** `frontend/components/funil/LeadDetailsModal.tsx` — linha 55
- **Comentário:** `// TODO: Create client from lead`
- **Descrição:** O botão "Converter em Cliente" no modal de detalhes do lead apenas atualiza o estágio do lead, mas não cria efetivamente um registro de cliente no sistema.
- **Impacto:** Médio — fluxo de conversão do funil de vendas incompleto.

### 1.3 Persistência de Preferências de Notificação
- **Arquivo:** `frontend/components/configuracoes/NotificacoesTab.tsx` — linha 57
- **Comentário:** `// TODO: persist via PATCH /profile/preferences when backend endpoint is ready`
- **Descrição:** Os toggles de preferência de notificação funcionam na interface mas não salvam no backend. As alterações são perdidas ao recarregar a página.
- **Impacto:** Médio — configurações de notificação não persistem.

---

## 2. Funcionalidades "Em Breve" (Coming Soon)

### 2.1 Chat de IA — Mensagem ao Usuário
- **Arquivo:** `frontend/app/(dashboard)/central/page.tsx` — linha 50
- **Mensagem exibida:** *"Funcionalidade de IA em desenvolvimento. Em breve você poderá conversar com nossos agentes inteligentes para obter informações sobre processos, prazos e muito mais."*
- **Descrição:** Quando o usuário envia uma mensagem na Central de IA, recebe esta resposta genérica em vez de uma resposta real do agente.
- **Impacto:** Alto — experiência do usuário indica que o recurso não está pronto.

### 2.2 Histórico de Interações do Lead
- **Arquivo:** `frontend/components/funil/LeadDetailsModal.tsx` — linha 223
- **Mensagem exibida:** *"Histórico completo de interações será implementado em breve"*
- **Descrição:** Na aba "Interações" do modal de detalhes do lead, apenas uma mensagem placeholder é exibida ao invés do histórico real.
- **Impacto:** Baixo — funcionalidade secundária do CRM.

### 2.3 Autenticação de Dois Fatores (2FA)
- **Arquivo:** `frontend/components/configuracoes/SegurancaTab.tsx` — linhas 236-240
- **Mensagem exibida:** *"Em breve disponível. Proteja sua conta com Google Authenticator ou similar."*
- **Descrição:** O botão de configurar 2FA está desabilitado (`disabled`) e exibe "Em breve". A funcionalidade de autenticação por aplicativo autenticador não foi implementada.
- **Impacto:** Médio — funcionalidade de segurança importante ausente.

---

## 3. Links Placeholder (`href="#"`)

### 3.1 Esqueceu a Senha
- **Arquivo:** `frontend/app/(auth)/login/page.tsx` — linha 634
- **Elemento:** `<a href="#">Esqueceu a senha?</a>`
- **Descrição:** O link "Esqueceu a senha?" na tela de login não direciona para nenhuma página de recuperação de senha.
- **Impacto:** Alto — usuários não conseguem recuperar suas senhas.

### 3.2 Ver Todos (Atenção Imediata)
- **Arquivo:** `frontend/app/(dashboard)/dashboard/page.tsx` — linha 80
- **Elemento:** `<a href="#">Ver Todos</a>` no card "Atenção Imediata"
- **Descrição:** O link "Ver Todos" na seção de casos que requerem atenção imediata não navega para nenhuma página.
- **Impacto:** Baixo — funcionalidade de navegação auxiliar.

### 3.3 Histórico de Decisões Favoráveis
- **Arquivo:** `frontend/app/(dashboard)/dashboard/page.tsx` — linha 182
- **Elemento:** `<a href="#">Histórico</a>` no card "Decisões Favoráveis"
- **Descrição:** O link "Histórico" na seção de decisões favoráveis não navega para nenhuma página de histórico.
- **Impacto:** Baixo — funcionalidade de navegação auxiliar.

---

## Tabela Consolidada

| # | Funcionalidade | Arquivo | Tipo | Impacto | Status |
|---|---------------|---------|------|---------|--------|
| 1 | Integração AI Chat | `central/page.tsx` | TODO | Alto | Respostas mockadas |
| 2 | Conversão Lead → Cliente | `LeadDetailsModal.tsx` | TODO | Médio | Parcialmente implementado |
| 3 | Salvar Preferências Notificação | `NotificacoesTab.tsx` | TODO | Médio | Só UI, sem backend |
| 4 | Chat IA (mensagem ao usuário) | `central/page.tsx` | Em Breve | Alto | Exibe msg placeholder |
| 5 | Histórico de Interações | `LeadDetailsModal.tsx` | Em Breve | Baixo | Só placeholder |
| 6 | Autenticação 2FA | `SegurancaTab.tsx` | Em Breve | Médio | Desabilitado |
| 7 | Recuperação de Senha | `login/page.tsx` | Link `#` | Alto | Não implementado |
| 8 | Ver Todos (Atenção Imediata) | `dashboard/page.tsx` | Link `#` | Baixo | Não implementado |
| 9 | Histórico Decisões | `dashboard/page.tsx` | Link `#` | Baixo | Não implementado |

---

## Arquivos Afetados (6)

1. `frontend/app/(dashboard)/central/page.tsx`
2. `frontend/app/(dashboard)/dashboard/page.tsx`
3. `frontend/app/(auth)/login/page.tsx`
4. `frontend/components/funil/LeadDetailsModal.tsx`
5. `frontend/components/configuracoes/NotificacoesTab.tsx`
6. `frontend/components/configuracoes/SegurancaTab.tsx`

---

## Recomendações de Prioridade

### Prioridade Alta
1. **Recuperação de Senha** — Funcionalidade essencial de autenticação
2. **Integração AI Chat** — Feature principal do produto

### Prioridade Média
3. **Autenticação 2FA** — Segurança da conta
4. **Conversão Lead → Cliente** — Fluxo de negócio do CRM
5. **Persistência de Notificações** — UX de configurações

### Prioridade Baixa
6. **Histórico de Interações do Lead** — Feature complementar
7. **Link "Ver Todos"** — Navegação auxiliar
8. **Link "Histórico Decisões"** — Navegação auxiliar
