# Requirements Document - JusMonitorIA CRM Orquestrador

## Introduction

O JusMonitorIA é um Micro-SaaS B2B que oferece monitoramento automatizado de processos jurídicos para escritórios de advocacia. O sistema integra-se com a API DataJud do CNJ para consultar atualizações processuais, gerencia leads e clientes, e utiliza embeddings semânticos para classificação inteligente de movimentações processuais. Como plataforma multi-tenant, o JusMonitorIA garante isolamento completo de dados entre diferentes escritórios.

## Glossary

- **JusMonitorIA**: O sistema completo de CRM e orquestrador de monitoramento processual
- **DataJud_API**: API oficial do CNJ para consulta de processos judiciais
- **Escritório**: Tenant/cliente do sistema (escritório de advocacia)
- **Tenant_ID**: Identificador único do escritório que garante isolamento de dados
- **Processo**: Processo judicial monitorado pelo sistema
- **Lead**: Potencial cliente em processo de captação
- **Cliente**: Escritório ou pessoa física que contratou serviços jurídicos
- **Movimentação**: Atualização ou evento em um processo judicial
- **Embedding**: Representação vetorial semântica de texto gerada via LiteLLM
- **Taskiq**: Sistema de filas assíncronas para processamento em background
- **FastAPI_Gateway**: API REST principal do sistema
- **Rate_Limit**: Limite de requisições por período de tempo imposto pela API externa
- **Batch**: Agrupamento de requisições para processamento em lote

## Requirements

### Requirement 1: Isolamento Multi-Tenant

**User Story:** Como administrador do sistema, eu quero garantir isolamento completo de dados entre escritórios, para que cada tenant acesse apenas seus próprios dados.

#### Acceptance Criteria

1. THE JusMonitorIA SHALL associar todos os registros de Clientes, Processos, Leads e Tags com um Tenant_ID
2. WHEN um usuário autenticado faz uma consulta, THE JusMonitorIA SHALL filtrar automaticamente os resultados pelo Tenant_ID do usuário
3. THE JusMonitorIA SHALL rejeitar qualquer tentativa de acesso a dados de outro Tenant_ID
4. WHEN um novo registro é criado, THE JusMonitorIA SHALL atribuir automaticamente o Tenant_ID do usuário autenticado
5. THE JusMonitorIA SHALL validar a presença de Tenant_ID em todas as operações de leitura e escrita no banco de dados

### Requirement 2: Autenticação e Autorização

**User Story:** Como usuário do sistema, eu quero fazer login de forma segura, para que apenas pessoas autorizadas acessem o JusMonitorIA.

#### Acceptance Criteria

1. WHEN um usuário fornece credenciais válidas, THE JusMonitorIA SHALL gerar um token JWT contendo o Tenant_ID
2. THE JusMonitorIA SHALL validar o token JWT em todas as requisições protegidas
3. WHEN um token expirado é apresentado, THE JusMonitorIA SHALL retornar erro 401 e solicitar nova autenticação
4. THE JusMonitorIA SHALL armazenar senhas usando hash bcrypt com salt
5. WHEN um usuário pertence a múltiplos escritórios, THE JusMonitorIA SHALL permitir seleção do Tenant_ID ativo

### Requirement 3: Cadastro de Clientes

**User Story:** Como advogado, eu quero cadastrar clientes no sistema, para que eu possa associá-los aos processos monitorados.

#### Acceptance Criteria

1. WHEN um cliente é cadastrado, THE JusMonitorIA SHALL armazenar nome, CPF/CNPJ, email e telefone associados ao Tenant_ID
2. THE JusMonitorIA SHALL validar unicidade de CPF/CNPJ dentro do mesmo Tenant_ID
3. WHEN dados obrigatórios estão ausentes, THE JusMonitorIA SHALL retornar erro de validação
4. THE JusMonitorIA SHALL permitir atualização de dados cadastrais de clientes do mesmo Tenant_ID

### Requirement 4: Cadastro de Processos

**User Story:** Como advogado, eu quero cadastrar processos para monitoramento, para que o sistema acompanhe automaticamente suas atualizações.

#### Acceptance Criteria

1. WHEN um processo é cadastrado, THE JusMonitorIA SHALL armazenar o número CNJ, cliente associado, tribunal e Tenant_ID
2. THE JusMonitorIA SHALL validar o formato do número CNJ (padrão NNNNNNN-DD.AAAA.J.TR.OOOO)
3. WHEN um processo já existe para o mesmo Tenant_ID, THE JusMonitorIA SHALL retornar erro de duplicação
4. THE JusMonitorIA SHALL permitir associar múltiplos clientes ao mesmo processo dentro do Tenant_ID

### Requirement 5: Gestão de Leads

**User Story:** Como gestor comercial, eu quero gerenciar leads de potenciais clientes, para que eu possa acompanhar o funil de vendas.

#### Acceptance Criteria

1. WHEN um lead é criado, THE JusMonitorIA SHALL armazenar nome, email, telefone, origem e Tenant_ID
2. THE JusMonitorIA SHALL permitir atribuir status ao lead (novo, contatado, qualificado, convertido, perdido)
3. WHEN um lead é convertido, THE JusMonitorIA SHALL permitir criar um Cliente associado ao mesmo Tenant_ID
4. THE JusMonitorIA SHALL registrar histórico de interações com cada lead

### Requirement 6: Sistema de Tags

**User Story:** Como usuário, eu quero criar tags personalizadas, para que eu possa organizar e filtrar processos e clientes.

#### Acceptance Criteria

1. WHEN uma tag é criada, THE JusMonitorIA SHALL armazenar nome, cor e Tenant_ID
2. THE JusMonitorIA SHALL permitir associar tags a Processos, Clientes e Leads do mesmo Tenant_ID
3. THE JusMonitorIA SHALL validar unicidade de nome de tag dentro do mesmo Tenant_ID
4. WHEN uma tag é excluída, THE JusMonitorIA SHALL remover todas as associações dessa tag

### Requirement 7: Geração de Embeddings Semânticos

**User Story:** Como desenvolvedor, eu quero gerar embeddings de movimentações processuais, para que o sistema possa classificar automaticamente a relevância das atualizações.

#### Acceptance Criteria

1. WHEN uma movimentação processual é recebida, THE JusMonitorIA SHALL gerar o embedding de forma assíncrona via Taskiq
2. THE JusMonitorIA SHALL utilizar LiteLLM para gerar embeddings vetoriais do texto da movimentação
3. THE JusMonitorIA SHALL armazenar o vetor de embedding associado à movimentação
4. IF a geração de embedding falhar, THEN THE JusMonitorIA SHALL registrar o erro e permitir reprocessamento posterior
5. THE FastAPI_Gateway SHALL retornar resposta imediata sem aguardar conclusão da geração de embedding

### Requirement 8: Classificação de Movimentações

**User Story:** Como advogado, eu quero que movimentações sejam classificadas automaticamente por relevância, para que eu priorize as mais importantes.

#### Acceptance Criteria

1. WHEN um embedding é gerado, THE JusMonitorIA SHALL calcular similaridade com embeddings de referência
2. THE JusMonitorIA SHALL atribuir score de relevância baseado na similaridade semântica
3. THE JusMonitorIA SHALL classificar movimentações em categorias (crítica, alta, média, baixa)
4. WHEN uma movimentação é classificada como crítica, THE JusMonitorIA SHALL marcar para notificação prioritária

### Requirement 9: Consulta Manual de Processos

**User Story:** Como advogado, eu quero consultar manualmente um processo no DataJud, para que eu possa verificar atualizações sob demanda.

#### Acceptance Criteria

1. WHEN um usuário solicita consulta manual, THE JusMonitorIA SHALL enviar requisição à DataJud_API com o número CNJ
2. THE JusMonitorIA SHALL retornar as movimentações mais recentes do processo
3. IF a DataJud_API retornar erro, THEN THE JusMonitorIA SHALL exibir mensagem descritiva ao usuário
4. THE JusMonitorIA SHALL registrar timestamp da última consulta manual

### Requirement 10: Agendamento de Monitoramento Automático

**User Story:** Como usuário, eu quero que processos sejam consultados automaticamente a cada 6 horas, para que eu receba atualizações sem intervenção manual.

#### Acceptance Criteria

1. THE JusMonitorIA SHALL agendar consultas automáticas via Taskiq a cada 6 horas para todos os processos ativos
2. WHEN o horário de consulta é atingido, THE JusMonitorIA SHALL enfileirar tarefas de consulta ao DataJud
3. THE JusMonitorIA SHALL processar apenas processos do Tenant_ID correspondente em cada tarefa
4. WHEN uma consulta automática é concluída, THE JusMonitorIA SHALL atualizar o timestamp de última verificação

### Requirement 11: Rate Limiting e Cidadania na API DataJud

**User Story:** Como administrador do sistema, eu quero respeitar os limites da API do CNJ, para que o sistema não seja bloqueado por excesso de requisições.

#### Acceptance Criteria

1. THE JusMonitorIA SHALL agrupar consultas ao DataJud_API em lotes (batches) de no máximo 100 processos por lote
2. THE JusMonitorIA SHALL respeitar o Rate_Limit da DataJud_API distribuindo a carga via Taskiq ao longo das 6 horas
3. WHEN um escritório possui 5.000 processos, THE JusMonitorIA SHALL distribuir as consultas em 50 batches espaçados uniformemente
4. IF a DataJud_API retornar erro 429 (Too Many Requests), THEN THE JusMonitorIA SHALL aplicar backoff exponencial antes de retentar
5. THE JusMonitorIA SHALL registrar métricas de consumo de API por Tenant_ID para monitoramento

### Requirement 12: Detecção de Novas Movimentações

**User Story:** Como advogado, eu quero ser notificado apenas de movimentações novas, para que eu não receba alertas duplicados.

#### Acceptance Criteria

1. WHEN movimentações são recebidas da DataJud_API, THE JusMonitorIA SHALL comparar com movimentações já armazenadas
2. THE JusMonitorIA SHALL identificar movimentações novas baseado em hash do conteúdo
3. THE JusMonitorIA SHALL armazenar apenas movimentações que não existem no banco de dados
4. WHEN uma movimentação nova é detectada, THE JusMonitorIA SHALL acionar o fluxo de geração de embedding

### Requirement 13: Notificações por Email

**User Story:** Como advogado, eu quero receber emails sobre atualizações críticas, para que eu possa agir rapidamente.

#### Acceptance Criteria

1. WHEN uma movimentação crítica é detectada, THE JusMonitorIA SHALL enviar email ao responsável pelo processo
2. THE JusMonitorIA SHALL incluir no email o número do processo, cliente, e resumo da movimentação
3. THE JusMonitorIA SHALL permitir configurar preferências de notificação por usuário
4. WHEN o envio de email falhar, THE JusMonitorIA SHALL registrar o erro e tentar reenvio após 5 minutos

### Requirement 14: Dashboard de Processos

**User Story:** Como advogado, eu quero visualizar todos os meus processos em um dashboard, para que eu tenha visão geral do portfólio.

#### Acceptance Criteria

1. THE JusMonitorIA SHALL exibir lista de processos filtrada pelo Tenant_ID do usuário autenticado
2. THE JusMonitorIA SHALL permitir filtrar processos por cliente, status, tribunal e tags
3. THE JusMonitorIA SHALL exibir indicadores visuais para processos com movimentações críticas não lidas
4. THE JusMonitorIA SHALL ordenar processos por data da última movimentação por padrão

### Requirement 15: Histórico de Movimentações

**User Story:** Como advogado, eu quero visualizar o histórico completo de um processo, para que eu possa acompanhar sua evolução.

#### Acceptance Criteria

1. WHEN um processo é selecionado, THE JusMonitorIA SHALL exibir todas as movimentações em ordem cronológica reversa
2. THE JusMonitorIA SHALL exibir para cada movimentação a data, tipo, descrição e classificação de relevância
3. THE JusMonitorIA SHALL permitir marcar movimentações como lidas
4. THE JusMonitorIA SHALL destacar visualmente movimentações não lidas

### Requirement 16: Busca Semântica de Processos

**User Story:** Como advogado, eu quero buscar processos por similaridade semântica, para que eu encontre casos relacionados.

#### Acceptance Criteria

1. WHEN um usuário fornece texto de busca, THE JusMonitorIA SHALL gerar embedding da consulta
2. THE JusMonitorIA SHALL calcular similaridade com embeddings de movimentações do mesmo Tenant_ID
3. THE JusMonitorIA SHALL retornar processos ordenados por relevância semântica
4. THE JusMonitorIA SHALL limitar resultados aos processos do Tenant_ID do usuário

### Requirement 17: Exportação de Relatórios

**User Story:** Como gestor, eu quero exportar relatórios de processos, para que eu possa analisar dados externamente.

#### Acceptance Criteria

1. THE JusMonitorIA SHALL permitir exportar lista de processos em formato CSV e PDF
2. THE JusMonitorIA SHALL incluir no relatório apenas dados do Tenant_ID do usuário
3. WHEN um relatório é solicitado, THE JusMonitorIA SHALL gerar o arquivo de forma assíncrona via Taskiq
4. THE JusMonitorIA SHALL notificar o usuário quando o relatório estiver pronto para download

### Requirement 18: Auditoria de Acessos

**User Story:** Como administrador, eu quero registrar todos os acessos ao sistema, para que eu possa auditar atividades suspeitas.

#### Acceptance Criteria

1. THE JusMonitorIA SHALL registrar timestamp, usuário, Tenant_ID, ação e IP de origem para cada operação
2. THE JusMonitorIA SHALL armazenar logs de auditoria em tabela separada com retenção de 12 meses
3. THE JusMonitorIA SHALL permitir consultar logs filtrados por Tenant_ID, usuário e período
4. WHEN uma tentativa de acesso não autorizado ocorre, THE JusMonitorIA SHALL registrar o evento com flag de alerta

### Requirement 19: Backup Automático

**User Story:** Como administrador, eu quero backups automáticos do banco de dados, para que eu possa recuperar dados em caso de falha.

#### Acceptance Criteria

1. THE JusMonitorIA SHALL executar backup completo do banco de dados diariamente às 03:00 AM
2. THE JusMonitorIA SHALL armazenar backups em storage externo com criptografia
3. THE JusMonitorIA SHALL manter backups dos últimos 30 dias
4. WHEN um backup falhar, THE JusMonitorIA SHALL enviar alerta ao administrador do sistema

### Requirement 20: Healthcheck e Monitoramento

**User Story:** Como DevOps, eu quero endpoints de healthcheck, para que eu possa monitorar a saúde do sistema.

#### Acceptance Criteria

1. THE JusMonitorIA SHALL expor endpoint /health que retorna status 200 quando operacional
2. THE JusMonitorIA SHALL verificar conectividade com banco de dados, Redis e Taskiq no healthcheck
3. WHEN algum componente crítico está indisponível, THE JusMonitorIA SHALL retornar status 503
4. THE JusMonitorIA SHALL expor métricas Prometheus em endpoint /metrics

### Requirement 21: Tratamento de Erros da API DataJud

**User Story:** Como desenvolvedor, eu quero tratamento robusto de erros da API externa, para que falhas temporárias não quebrem o sistema.

#### Acceptance Criteria

1. WHEN a DataJud_API retorna erro 5xx, THE JusMonitorIA SHALL retentar a requisição até 3 vezes com backoff exponencial
2. IF todas as tentativas falharem, THEN THE JusMonitorIA SHALL registrar o erro e agendar nova tentativa em 1 hora
3. WHEN a DataJud_API está indisponível, THE JusMonitorIA SHALL continuar operando com dados em cache
4. THE JusMonitorIA SHALL expor dashboard de status da integração com DataJud_API

### Requirement 22: Configuração de Intervalos de Consulta

**User Story:** Como administrador de escritório, eu quero configurar o intervalo de consulta automática, para que eu possa ajustar conforme meu plano.

#### Acceptance Criteria

1. THE JusMonitorIA SHALL permitir configurar intervalo de consulta por Tenant_ID (1h, 6h, 12h, 24h)
2. WHEN o intervalo é alterado, THE JusMonitorIA SHALL reagendar todas as tarefas do Tenant_ID
3. THE JusMonitorIA SHALL validar que o intervalo mínimo respeita o Rate_Limit da DataJud_API
4. THE JusMonitorIA SHALL exibir consumo estimado de API baseado no intervalo configurado

### Requirement 23: Parser de Movimentações DataJud

**User Story:** Como desenvolvedor, eu quero parsear respostas da API DataJud, para que o sistema extraia dados estruturados.

#### Acceptance Criteria

1. WHEN uma resposta da DataJud_API é recebida, THE Parser SHALL extrair número CNJ, movimentações, partes e tribunal
2. WHEN uma resposta inválida é recebida, THE Parser SHALL retornar erro descritivo
3. THE Pretty_Printer SHALL formatar objetos de Movimentação de volta para o formato DataJud
4. FOR ALL objetos de Movimentação válidos, parsear então formatar então parsear SHALL produzir objeto equivalente (round-trip property)

### Requirement 24: Gestão de Usuários e Permissões

**User Story:** Como administrador de escritório, eu quero gerenciar usuários e suas permissões, para que eu controle quem acessa o que.

#### Acceptance Criteria

1. THE JusMonitorIA SHALL permitir criar usuários associados a um Tenant_ID
2. THE JusMonitorIA SHALL suportar roles (admin, advogado, assistente, visualizador)
3. WHEN um usuário com role visualizador tenta editar dados, THE JusMonitorIA SHALL retornar erro 403
4. THE JusMonitorIA SHALL permitir que admin do Tenant_ID gerencie usuários apenas do seu escritório

### Requirement 25: Integração com LiteLLM

**User Story:** Como desenvolvedor, eu quero integração com LiteLLM, para que o sistema gere embeddings usando diferentes provedores de LLM.

#### Acceptance Criteria

1. THE JusMonitorIA SHALL configurar LiteLLM com fallback entre múltiplos provedores (OpenAI, Anthropic, local)
2. WHEN um provedor falha, THE JusMonitorIA SHALL tentar automaticamente o próximo provedor configurado
3. THE JusMonitorIA SHALL registrar métricas de uso e custo por provedor
4. THE JusMonitorIA SHALL permitir configurar modelo de embedding por Tenant_ID

## Notes

Este documento define os requisitos funcionais e não-funcionais do JusMonitorIA CRM Orquestrador. As três melhorias críticas de arquitetura foram incorporadas:

1. **Multi-tenancy (Requirement 1)**: Isolamento completo via Tenant_ID em todas as entidades
2. **Rate Limiting (Requirement 11)**: Batching e distribuição de carga para respeitar limites da API DataJud
3. **Embeddings Assíncronos (Requirement 7)**: Geração via Taskiq sem bloquear o FastAPI Gateway

Todos os requisitos seguem padrões EARS e regras de qualidade INCOSE, garantindo clareza, testabilidade e completude.
