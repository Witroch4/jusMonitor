# Modelo de Interoperabilidade de Dados do Poder Judiciário

**Conselho Nacional de Justiça — CNJ**  
**Versão:** 2.2.2  
**Data:** Julho de 2014  
**Referência:** MNI — Modelo Nacional de Interoperabilidade  

---

## Sumário

1. [Contextualização](#1-contextualização)
2. [Versões](#2-versões)
3. [Mudanças Significativas](#3-mudanças-significativas)
   - 3.1 [Operações](#31-operações)
   - 3.2 [Mudanças em Objetos](#32-mudanças-em-objetos)
     - 3.2.1 [`tipoParte`](#321-httpcnjjusbrntercomunicacao-222tipoparte)
     - 3.2.2 [`modalidadeVinculacaoProcesso`](#322-modalidadevinculacaoprocesso)
     - 3.2.3 [`tipoNumeroUnico`](#323-tiponumerounico)
     - 3.2.4 [`tipoCabecalhoProcesso`](#324-tipocabecalhoprocesso)
     - 3.2.5 [`tipoMovimentoProcessual`](#325-tipomovimentoprocessual)
     - 3.2.6 [`tipoDocumento`](#326-tipodocumento)
     - 3.2.7 [`tipoAssinatura`](#327-tipoassinatura)
     - 3.2.8 [`tipoOrgaoJulgador`](#328-tipororgaojulgador)
     - 3.2.9 [`tipoSignatarioSimples`](#329-tiposignatoriosimples)
     - 3.2.10 [`tipoEntregarManifestacaoProcessualResposta`](#3210-tipoentregarmanifestacaoprocessualresposta)
     - 3.2.11 [`tipoConsultarProcesso`](#3211-tipoconsultarprocesso)
     - 3.2.12 [`tipoConfirmarRecebimento`](#3212-tipoconfirmarrecebimento)
     - 3.2.13 [`tipoConfirmarRecebimentoResposta`](#3213-tipoconfirmarrecebimentoresposta)
   - 3.3 [Dinâmica](#33-dinâmica)
     - 3.3.1 [Confirmação de Recebimento](#331-confirmação-de-recebimento)
4. [Visão Geral dos Objetos de Comunicação](#4-visão-geral-dos-objetos-de-comunicação)
5. [Serviços Ofertados](#5-serviços-ofertados)
   - 5.1 [Visão Geral das Operações](#51-visão-geral-das-operações)
   - 5.2 [Autenticação](#52-autenticação)
   - 5.3 [Autorização](#53-autorização)
6. [Dinâmica das Comunicações](#6-dinâmica-das-comunicações)
   - 6.1 [Entre Tribunais](#61-entre-tribunais)
   - 6.2 [Entre Tribunais e Outros Órgãos](#62-entre-tribunais-e-outros-órgãos-de-administração-da-justiça)
     - 6.2.1 [Protocolo Inicial](#621-protocolo-inicial)
     - 6.2.2 [Avisos de Comunicação](#622-avisos-de-comunicação)
     - 6.2.3 [Consulta de Comunicação](#623-consulta-de-comunicação)

---

## 1. Contextualização

Este documento se destina a estabelecer as bases para o **intercâmbio de informações de processos judiciais e assemelhados** entre os diversos órgãos de administração da Justiça.

Além de servir de base para a implementação das funcionalidades pertinentes no âmbito do sistema processual de que trata o **TCOT n.º 073/2009**, este modelo servirá como base de discussão para revisão do modelo já estabelecido em razão do acordo **TAC n.º 58/2009**.

---

## 2. Versões

| Versão | Autor / Revisor | Data | Modificação |
|--------|----------------|------|-------------|
| 1.9.0 | Paulo C. de Araújo Silva Filho | 03/08/10 | Inicial |
| 1.9.1 | Paulo C. de Araújo Silva Filho | 17/12/10 | Rascunho final |
| 2.0.0 | Grupo de Interoperabilidade | 14/03/11 | Versão final |
| 2.1.0 | Antonio Augusto Silva Martins / Paulo C. de Araújo Silva Filho | 30/04/12 | Inclusão de objetos solicitados pelos participantes do grupo. Correção do documento para a versão 2.1.0 |
| 2.2.1 | Guilherme Alves Reis | 28/01/14 | Ajustes destinados a viabilizar o envio de grandes volumes de dados |
| 2.2.2 | Paulo C. de Araújo Silva Filho | 07/07/14 | Ajustes decorrentes da 2ª reunião do comitê-técnico do MNI. Redução da repetição de informações entre este documento e os documentos de definição, com vistas a reduzir ambiguidades. Renumeração dos capítulos em razão da introdução de capítulo de modificações relevantes. |

---

## 3. Mudanças Significativas

Este capítulo identifica as mudanças significativas entre a versão atual (**2.2.2**) e a última versão em produção (**2.1.1**), a fim de permitir que implementadores do modelo possam organizar seu trabalho de evolução mais eficientemente.

---

### 3.1. Operações

Foi incluída a operação **`confirmarRecebimento`**, com:

- **Parâmetro de entrada:** `confirmarRecebimento`
- **Parâmetro de saída:** `confirmarRecebimentoResposta`
- Criadas as correspondentes mensagens e bindings no WSDL.

A operação **`tipoConsultarProcesso`** teve incluída a possibilidade de **não recuperar o cabeçalho processual**.

---

### 3.2. Mudanças em Objetos

#### 3.2.1. `tipoParte`

**Namespace:** `http://www.cnj.jus.br/intercomunicacao-2.2.2`

- Alterada a designação do elemento `interesse-publico` para **`interessePublico`** (remoção do hífen, adequação ao padrão camelCase).

---

#### 3.2.2. `modalidadeVinculacaoProcesso`

**Namespace:** `http://www.cnj.jus.br/intercomunicacao-2.2.2`

Acrescentadas **quatro novas modalidades** de vinculação processual:

| Código | Descrição |
|--------|-----------|
| `AR` | Ação Rescisória |
| `CD` | Competência Delegada |
| `RR` | Recurso Repetitivo |
| `RG` | Repercussão Geral |

---

#### 3.2.3. `tipoNumeroUnico`

**Namespace:** `http://www.cnj.jus.br/intercomunicacao-2.2.2`

Reduzidas as restrições do padrão esperado:

| Antes | Depois |
|-------|--------|
| `\d{13}[0-29][0-7]\d{4}` | `\d{20}` |

---

#### 3.2.4. `tipoCabecalhoProcesso`

**Namespace:** `http://www.cnj.jus.br/intercomunicacao-2.2.2`

- **Suprimido** o atributo `codigoOrgaoJulgador`.
- **Acrescentado** o atributo `dataAjuizamento` do tipo complexo `tipoDataHora`.
- **Acrescentado** o elemento `orgaoJulgador` do tipo complexo (novo) `tipoOrgaoJulgador`, com **ocorrência obrigatória**.
- **Acrescentado** o elemento `outrosNumeros`, do tipo `String`, com **ocorrência facultativa e múltipla**.

---

#### 3.2.5. `tipoMovimentoProcessual`

**Namespace:** `http://www.cnj.jus.br/intercomunicacao-2.2.2`

- O elemento `movimentoLocal` teve seu tipo modificado de `String` para o tipo complexo **`tipoMovimentoLocal`**.

---

#### 3.2.6. `tipoDocumento`

**Namespace:** `http://www.cnj.jus.br/intercomunicacao-2.2.2`

- Modificado o tipo do elemento `conteudo` de `hexBinary` para **`base64Binary`**, com conteúdo esperado `application/octet-stream`.
- Alterada a semântica do atributo `tipoDocumento` para passar a exigir o **código nacional** previsto nas TNUs da **Resolução CNJ 46**.
- Incluído atributo opcional **`descricao`** do tipo `String` para descrição do documento.
- Incluído atributo opcional **`tipoDocumentoLocal`**, do tipo `String`, para indicação de código local (do tribunal) de armazenamento.

---

#### 3.2.7. `tipoAssinatura`

**Namespace:** `http://www.cnj.jus.br/intercomunicacao-2.2.2`

- Modificado o tipo de extensão do tipo simples `string` para **tipo complexo**.
- Modificado o tipo do atributo `dataAssinatura` de `String` para o tipo complexo **`tipoDataHora`**.
- Incluído o atributo facultativo **`codificacaoCertificado`**, do tipo `String`.
- Incluído o elemento **facultativo e múltiplo** do tipo complexo (novo) **`tipoSignatarioSimples`**.

---

#### 3.2.8. `tipoOrgaoJulgador`

**Namespace:** `http://www.cnj.jus.br/intercomunicacao-2.2.2`

Incluído esse **novo tipo complexo**, que contém os seguintes atributos **obrigatórios**:

| Atributo | Tipo | Descrição |
|----------|------|-----------|
| `codigoOrgao` | `string` | Código identificador do órgão julgador |
| `nomeOrgao` | `string` | Nome do órgão julgador |
| `codigoMunicipioIBGE` | `int` | Código IBGE do município |
| `instancia` | enum | Instância do órgão: `ORIG`, `REV`, `ESP`, `EXT`, `ADM` |

---

#### 3.2.9. `tipoSignatarioSimples`

**Namespace:** `http://www.cnj.jus.br/intercomunicacao-2.2.2`

Incluído esse **novo tipo complexo**, que contém os seguintes atributos **obrigatórios**:

| Atributo | Tipo | Descrição |
|----------|------|-----------|
| `identificador` | `string` | Identificador do signatário |
| `dataHora` | `tipoDataHora` | Data e hora da assinatura |

---

#### 3.2.10. `tipoEntregarManifestacaoProcessualResposta`

**Namespace:** `http://www.cnj.jus.br/tipos-servico-intercomunicacao-2.2.2`

- Modificado o tipo do elemento `recibo` de `hexBinary` para **`base64Binary`**, com conteúdo esperado `application/octet-stream`.

---

#### 3.2.11. `tipoConsultarProcesso`

**Namespace:** `http://www.cnj.jus.br/tipos-servico-intercomunicacao-2.2.2`

- Incluído o elemento **`incluirCabecalho`** com o objetivo de indicar se o consulente deseja receber o cabeçalho processual quando da consulta de documentos.

---

#### 3.2.12. `tipoConfirmarRecebimento`

**Namespace:** `http://www.cnj.jus.br/tipos-servico-intercomunicacao-2.2.2`

Incluído esse **novo tipo complexo**, para utilização na operação de confirmação de recebimento:

| Atributo | Tipo | Descrição |
|----------|------|-----------|
| `idRecebedor` | `string` | Identificador do tribunal recebedor |
| `senhaRecebedor` | `string` | Senha do tribunal recebedor |
| `protocolo` | `string` | Número do protocolo da manifestação recebida |

---

#### 3.2.13. `tipoConfirmarRecebimentoResposta`

**Namespace:** `http://www.cnj.jus.br/tipos-servico-intercomunicacao-2.2.2`

Incluído esse **novo tipo complexo**, para utilização na resposta da operação de confirmação de recebimento:

| Atributo | Tipo | Descrição |
|----------|------|-----------|
| `sucesso` | `boolean` | Indica se a confirmação foi bem-sucedida |
| `mensagem` | `string` | Mensagem informativa sobre o resultado |

---

### 3.3. Dinâmica

#### 3.3.1. Confirmação de Recebimento

Incluída a operação de **confirmação de recebimento** com o objetivo de um tribunal recebedor de uma entrega de manifestação processual parcial de outro tribunal poder **comunicar o recebimento integral** da manifestação.

---

## 4. Visão Geral dos Objetos de Comunicação

A definição clara de elementos de comunicação — ou **objetos de comunicação** — é determinante do sucesso da interoperabilidade.

No presente modelo, a opção se deu pelo uso de **dois arquivos definidores de esquema (XSD — XML Schema Document)** que descrevem esses objetos, permitindo o intercâmbio de dados independentemente das implementações existentes em cada órgão.

Os documentos XSD respectivos devem ser publicados juntamente com o presente arquivo. A documentação de referência pode ser gerada a partir desses arquivos.

---

### Arquivo: `Intercomunicacao-2.2.2.xsd`

| Campo | Valor |
|-------|-------|
| **Localização** | `http://www.cnj.jus.br/intercomunicacao-2.2.2/` |
| **Namespace** | `http://www.cnj.jus.br/intercomunicacao-2.2.2` |

**Objetos definidos:**

| Tipo | Categoria |
|------|-----------|
| `tipoAssinatura` | Assinatura digital |
| `tipoAssuntoLocal` | Assunto local do tribunal |
| `tipoAssuntoProcessual` | Assunto processual nacional |
| `tipoAvisoComunicacaoPendente` | Aviso de comunicação pendente |
| `tipoCabecalhoProcesso` | Cabeçalho do processo |
| `tipoComunicacaoProcessual` | Comunicação processual |
| `tipoDocumento` | Documento processual |
| `tipoDocumentoIdentificacao` | Documento de identificação |
| `tipoEndereco` | Endereço |
| `tipoIntercomunicacao` | Elemento raiz de intercomunicação |
| `tipoMovimentoLocal` | Movimento local do tribunal |
| `tipoMovimentoNacional` | Movimento nacional (TPU) |
| `tipoMovimentoProcessual` | Movimento processual |
| `tipoOrgaoJulgador` | Órgão julgador *(novo na 2.2.2)* |
| `tipoParametro` | Parâmetro genérico |
| `tipoParte` | Parte processual |
| `tipoPessoa` | Pessoa (física ou jurídica) |
| `tipoPoloProcessual` | Polo processual |
| `tipoProcessoJudicial` | Processo judicial completo |
| `tipoRelacionamentoPessoal` | Relacionamento entre pessoas |
| `tipoRepresentanteProcessual` | Representante processual |
| `tipoSignatarioSimples` | Signatário simples *(novo na 2.2.2)* |
| `tipoVinculacaoProcessual` | Vinculação entre processos |
| `identificadorComunicacao` | Identificador de comunicação |
| `modalidadeDocumentoIdentificador` | Modalidade de documento identificador |
| `modalidadeGeneroPessoa` | Gênero da pessoa |
| `modalidadePoloProcessual` | Polo processual (ativo, passivo, etc.) |
| `modalidadeRelacionamentoPessoal` | Tipo de relacionamento |
| `modalidadeRepresentanteProcessual` | Tipo de representante |
| `modalidadeVinculacaoProcesso` | Modalidade de vinculação processual |
| `tipoCadastroIdentificador` | Cadastro de identificador |
| `tipoCadastroOAB` | Cadastro OAB |
| `tipoComplemento` | Complemento de assunto/movimento |
| `tipoComunicacao` | Comunicação processual |
| `tipoData` | Data no formato nacional |
| `tipoDataHora` | Data e hora no formato nacional |
| `tipoNumeroUnico` | Número único processual (CNJ) |
| `tipoPrazo` | Prazo processual |
| `tipoQualificacaoPessoa` | Qualificação da pessoa |

---

### Arquivo: `Tipos-servico-intercomunicacao-2.2.2.xsd`

| Campo | Valor |
|-------|-------|
| **Localização** | `http://www.cnj.jus.br/intercomunicacao-2.2.2/` |
| **Namespace** | `http://www.cnj.jus.br/tipos-servico-intercomunicacao-2.2.2` |

**Objetos definidos:**

| Tipo | Descrição |
|------|-----------|
| `tipoConfirmarRecebimento` | Parâmetros de entrada da operação de confirmação *(novo na 2.2.2)* |
| `tipoConfirmarRecebimentoResposta` | Resposta da operação de confirmação *(novo na 2.2.2)* |
| `tipoConsultaAlteracao` | Parâmetros de consulta de alteração |
| `tipoConsultaAlteracaoResposta` | Resposta da consulta de alteração |
| `tipoConsultaAvisosPendentes` | Parâmetros de consulta de avisos pendentes |
| `tipoConsultaAvisosPendentesResposta` | Resposta da consulta de avisos pendentes |
| `tipoConsultaProcesso` | Parâmetros de consulta de processo |
| `tipoConsultaProcessoResposta` | Resposta da consulta de processo |
| `tipoConsultaTeorComunicacao` | Parâmetros de consulta de teor de comunicação |
| `tipoConsultaTeorComunicacaoResposta` | Resposta da consulta de teor de comunicação |
| `tipoEntregaManifestacaoProcessual` | Parâmetros da entrega de manifestação |
| `tipoEntregaManifestacaoProcessualResposta` | Resposta da entrega de manifestação |

> **Nota:** O arquivo `intercomunicacao-2.2.2.xsd` define os objetos básicos para troca de informações processuais, incluindo dados de cabeçalhos, movimentações, assuntos, classes, polos processuais, partes do processo, documentos e tipos de documentos.  
> O elemento raiz `intercomunicacao` permite encapsular quaisquer desses dados em um só tipo de elemento.  
> O arquivo `tipos-servico-intercomunicacao-2.2.2.xsd` define os tipos de elementos utilizados nas operações dos serviços WEB, encapsulando os objetos do arquivo anterior e acrescentando outros elementos informativos para as operações.

A partir dos elementos acima, foi elaborado o documento **WSDL** de modelo de um serviço de comunicação processual a ser ofertado por um tribunal.

---

## 5. Serviços Ofertados

A comunicação processual se dará a partir do arquétipo presente no arquivo **WSDL**, editado para refletir os dados de acesso próprios de cada tribunal ofertante do serviço.

---

### 5.1 Visão Geral das Operações

Todas as operações têm **um só parâmetro de entrada** e **um só parâmetro de saída**, sendo eles de tipos que encapsulam duas informações básicas e o efetivo resultado da operação.

Os dois elementos básicos contidos nos objetos de resposta são:
1. Um **booleano** indicando o sucesso ou não da operação.
2. Um **campo de texto** destinado à apresentação de alguma mensagem sobre a operação.

Os demais elementos são a resposta efetiva à operação, quando existente.

#### Tabela de Operações

| Seq | Nome da Operação | Parâmetro de Entrada | Parâmetro de Saída |
|-----|-----------------|---------------------|-------------------|
| 1 | `consultarAvisosPendentes` | `consultarAvisosPendentes` | `consultarAvisosPendentesResposta` |
| 2 | `consultarTeorComunicacao` | `consultarTeorComunicacao` | `consultarTeorComunicacaoResposta` |
| 3 | `consultarProcesso` | `consultarProcesso` | `consultarProcessoResponse` |
| 4 | `entregarManifestacaoProcessual` | `entregarManifestacaoProcessual` | `entregarManifestacaoProcessualResposta` |
| 5 | `consultarAlteracao` | `consultarAlteracao` | `consultarAlteracaoResposta` |
| 6 | `confirmarRecebimento` | `confirmarRecebimento` | `confirmarRecebimentoResposta` |

#### Descrição Detalhada das Operações

| Seq | Operação | Descrição |
|-----|----------|-----------|
| 1 | `consultarAvisosPendentes` | Permite que o consultante verifique a existência de **avisos de comunicação processual pendentes** junto ao tribunal fornecedor do serviço. A consulta poderá ser **específica** em relação a uma parte representada ou **genérica**, relativa aos processos em que o consultante opera como órgão de representação processual (MP, Defensoria Pública, Advocacia Pública, escritório de advocacia ou advogado). O retorno é um objeto do tipo `tipoConsultarAvisosPendentesResponse`, contendo uma lista dos avisos pendentes de tipo `tipoAvisoComunicacaoPendente`. Caso não haja aviso pendente, será retornada uma lista de tamanho zero. |
| 2 | `consultarTeorComunicacao` | Permite a **consulta ao teor específico** de comunicação processual pendente. O retorno será um objeto do tipo `tipoConsultaTeorComunicacaoResponse`, contendo uma lista de zero ou mais objetos do tipo `tipoComunicacaoProcessual`. |
| 3 | `consultarProcesso` | Permite a **consulta a um processo judicial**. Não é necessário que o consultante seja representante de qualquer das partes componentes do processo. Retorna objeto do tipo `tipoConsultarProcessoResponse`, que contém um objeto do tipo `tipoProcessoJudicial`, caso o processo exista e possa ser acessado pelo consultante. A implementação deverá assegurar que o processo somente seja retornado se o **nível de sigilo interno permitir** a consulta pelo requerente. Os documentos do processo poderão encerrar apenas **binários encriptados**, cuja chave será fornecida na `consultaTeorComunicacao`, caso haja intimação pendente para o documento transferido. |
| 4 | `entregarManifestacaoProcessual` | Permite a **entrega de manifestação processual** por órgão de representação processual ou por advogado. Também permite a entrega de **petição inicial**, caso em que o parâmetro de entrada deverá incluir os dados básicos necessários à distribuição. Retorna objeto do tipo `tipoEntregarManifestacaoProcessualResponse` que contém o **número do protocolo**, a **data da operação** e, se bem-sucedida, um **documento PDF com o recibo** (em base64Binary). |
| 5 | `consultarAlteracao` | Permite uma **verificação rápida** quanto à existência de modificações havidas em um processo judicial. |
| 6 | `confirmarRecebimento` | Operação destinada **exclusivamente a tribunais** em sua intercomunicação. Tem por objetivo permitir que um tribunal que tenha sido objeto de uma operação de entrega de manifestação processual (operação 4) **confirme junto ao tribunal remetente** que a recebeu integralmente. |

---

### 5.2 Autenticação

O meio **preferencial** para a autenticação dos clientes no serviço deverá ser a **troca de certificados digitais expedidos no formato ICP-Brasil**.

A partir do certificado, o serviço deverá obter o **número identificador do consulente** (CNPJ ou CPF) e, com isso, validar os acessos independentemente do uso de um par login/senha.

#### Autenticação Alternativa

Caso tal meio de autenticação não seja possível no contexto do tribunal, dever-se-á utilizar o **par login/senha** para a autenticação, assegurando-se, porém, em qualquer situação, que o canal de comunicação entre as partes seja seguro (**HTTPS**).

#### Identificação entre Tribunais

No caso de comunicação entre tribunais, os códigos identificadores serão o resultado da conjunção dos campos **"J"**, **"TR"** e **"OOOO"** de que tratam, respectivamente, os parágrafos 4.º, 5.º e 6.º do art. 1.º da **Resolução CNJ 65**, com ou sem a concatenação de outros dígitos identificadores no caso de esses 7 dígitos não serem suficientes para a identificação unívoca do órgão remetente.

---

### 5.3 Autorização

Os serviços deverão autorizar o acesso a informações seguindo as regras definidas para cada operação.

No que concerne à autorização, deve ser observado o **nível de sigilo** pertinente ao acesso. Os níveis de sigilo adotados são os seguintes:

| Nível | Nome | Descrição |
|-------|------|-----------|
| **0** | Público | Objeto acessível a **todos os servidores do Judiciário e dos demais órgãos públicos** de colaboração na administração da Justiça, assim como aos advogados. |
| **1** | Segredo | Objeto acessível aos **servidores do Judiciário**, aos servidores dos órgãos públicos de colaboração na administração da Justiça e às **partes do processo** (inclusive advogados). |
| **2** | Sigilo Mínimo | Objeto acessível aos **servidores do Judiciário** e aos demais órgãos públicos de colaboração na administração da Justiça. |
| **3** | Sigilo Médio | Objeto acessível aos **servidores do órgão em que tramita o processo**, às partes que provocaram o incidente e àqueles que forem expressamente incluídos. |
| **4** | Sigilo Intenso | Objeto acessível a **classes de servidores qualificados** (magistrado, diretor de secretaria/escrivão, oficial de gabinete/assessor) do órgão em que tramita o processo, às partes que provocaram o incidente e àqueles que forem expressamente incluídos. |
| **5** | Sigilo Absoluto | Objeto acessível **apenas ao magistrado** do órgão em que tramita, aos servidores e demais usuários por ele indicados e às partes que provocaram o incidente. |

> **Regra de Implementação:** O tribunal que implementar o serviço deverá assegurar que esses níveis de sigilo sejam respeitados. Caso possua quantidade inferior de níveis de sigilo, deverá encaixar seus níveis no nível da relação acima que for idêntico ou naquele **mais intenso** que se aproximar do nível local avaliado.
>
> É de **responsabilidade dos consumidores dos serviços** assegurar o respeito aos limites decorrentes do nível de sigilo dos objetos repassados.

---

## 6. Dinâmica das Comunicações

---

### 6.1 Entre Tribunais

A comunicação entre tribunais será feita primordialmente por meio do uso das operações:

- `consultarProcesso`
- `entregarManifestacaoProcessual`
- `confirmarRecebimento`

#### Fluxo de Comunicação

```
Tribunal Remetente                              Tribunal Destino
       │                                               │
       │──── entregarManifestacaoProcessual ──────────>│
       │     (dados básicos do processo/recurso)       │
       │                                               │
       │<─── protocolo de acompanhamento ──────────────│
       │                                               │
       │     [Tribunal Destino consulta processo]      │
       │<──── consultarProcesso ────────────────────── │
       │      (complementa dados faltantes)            │
       │                                               │
       │<──── confirmarRecebimento ─────────────────── │
       │      (confirmação de recebimento integral)    │
       │                                               │
       │     [Após processamento no destino]           │
       │<──── entregarManifestacaoProcessual ──────────│
       │      (documentos de relevo)                   │
       │                                               │
```

#### Regras

1. O tribunal **remetente originário** enviará os dados básicos do processo ou recurso como uma **entrega de manifestação processual originária**, indicando todos os dados básicos para a distribuição no tribunal de destino.

2. O tribunal de destino, com o **código do órgão de origem** e o **número do processo judicial**, realizará uma operação de **consulta do processo de origem**, podendo complementar elementos e documentos necessários ao processamento, caso não tenham sido enviados na entrega originária.

3. Finalizada a operação de consulta, o tribunal recebedor da manifestação deve utilizar a operação de **confirmação de recebimento** para comunicar ao tribunal de origem que recebeu integralmente o processo.

4. Ao concluir o processamento na instância ou órgão de destino, o tribunal de destino realizará, no processo de origem, uma **entrega de manifestação processual** em que encaminhará os documentos de relevo para o processamento.

5. O tribunal de origem receberá do tribunal de destino o **número de protocolo** necessário para eventual acompanhamento do processo de destino por meio da operação de consulta.

6. O tribunal de origem e o tribunal de destino assegurarão que, para os processos relacionados entre si, haja **liberação de acesso recíproca** para a consulta.

> **Aplicabilidade:** Essas comunicações poderão se dar tanto no caso de **remessa e devolução de recursos** quanto no caso de **remessa e devolução de cartas** (precatórias, de ordem e rogatórias).

---

### 6.2 Entre Tribunais e Outros Órgãos de Administração da Justiça

---

#### 6.2.1 Protocolo Inicial

No **protocolo inicial**, a operação `entregarManifestacaoProcessual` será realizada com a **substituição** do elemento `numeroProcesso` pelo elemento `tipoCabecalhoProcesso`, fazendo constar, nesse cabeçalho, como número de processo, uma sequência de **20 dígitos zero (0)**.

##### Distribuição Eletrônica

A distribuição eletrônica e imediata, determinada pela **EC n.º 45/2004**, será feita a partir dos dados componentes do cabeçalho.

##### Conflito de Competências

Caso não seja possível essa distribuição imediata em razão de **conflitos entre as competências** da comarca ou subseção de destino:

1. A resposta deverá ser de **insucesso**, com o número do protocolo pertinente.
2. Deverá ser acompanhada de **lista de parâmetros** com nome `"competencia"` e valor descritivo das competências possíveis para escolha pelo protocolante em uma nova tentativa de protocolo.
3. Essa tentativa de protocolo deverá ser **mantida no órgão de destino** até as `23h59m59s` do dia útil seguinte, assim como os **hashes dos documentos** enviados na primeira tentativa.

##### Segunda Tentativa de Protocolo

Na tentativa seguinte de protocolo, o órgão protocolante deverá indicar, além do cabeçalho:

| Parâmetro | Nome | Valor |
|-----------|------|-------|
| 1 | `protocolo-originario` | Número de protocolo da primeira tentativa |
| 2 | `competencia` | Competência para a qual pretende a distribuição |

> **Regra de Prazo:** Se a tentativa bem-sucedida se der na janela de tempo referida (até às 23h59m59s do dia útil seguinte), o sistema do Judiciário deverá considerar como **concretizado o protocolo na data e hora do primeiro protocolo**.

---

#### 6.2.2 Avisos de Comunicação

Os atos de comunicação serão realizados de forma **passiva pelo Judiciário**, como previsto na **Lei n.º 11.419/2006, art. 5.º**, com a disponibilização no serviço dos avisos pertinentes.

##### Disponibilização pelo Judiciário

O Judiciário deverá disponibilizar, na **data da elaboração do ato de comunicação**, um **aviso de comunicação pendente** (objeto `avisoComunicacaoPendente`).

Esse aviso:
- Será **identificado univocamente**.
- Ficará disponível para consulta pelo **prazo previsto no art. 5.º** da Lei n.º 11.419/2006, ou seja:
  - Até a expiração do prazo de **10 (dez) dias** previsto no § 3.º; **ou**
  - Até o momento em que houver a **ciência por meio da operação de consulta** de comunicação processual.

##### Consulta de Avisos Pendentes

Cada operação de consulta de avisos pendentes deverá retornar ao consultante **todos os avisos de comunicação ainda pendentes**.

Na operação de consulta, o consulente poderá indicar:
- Seu **código identificador específico** (preferencialmente o CNPJ); **ou**
- O **código identificador da pessoa ou entidade** a respeito da qual pretende consultar.

##### Exemplo de Consulta pela AGU

A **Advocacia-Geral da União (AGU)** poderá apresentar a consulta indicando:

- **CNPJ próprio da AGU:** O sistema do Judiciário deverá retornar *TODOS* os avisos de comunicação pendentes relativos a *TODAS* as pessoas/entidades cadastradas como tendo a AGU como órgão de representação.
- **CNPJ de um órgão específico (ex: ANTT):** O sistema do Judiciário deverá retornar *TODOS* os avisos de comunicação pendentes relativos especificamente à ANTT.

---

#### 6.2.3 Consulta de Comunicação

A consulta de comunicação poderá ser feita de **duas maneiras distintas**:

| Forma | Descrição |
|-------|-----------|
| **a) Consulta direta** | Consulta direta à comunicação pendente |
| **b) Consulta indireta** | Consulta ao processo seguida de consulta à comunicação pendente |

##### Forma A — Consulta Direta

Basta o consultante, de posse dos dados obtidos no `avisoComunicacaoPendente`, realizar a **consulta da comunicação específica**.

##### Forma B — Consulta Indireta (via Processo)

1. A **consulta ao processo** em relação ao qual há comunicação pendente para o órgão consultante deverá retornar os documentos pertinentes à comunicação **encriptados** seguindo o algoritmo **SHA-1**, fazendo uso de chave específica — preferencialmente o **hash do arquivo original**.

2. Com a **consulta posterior à comunicação**, os hashes dos documentos pertinentes à comunicação serão enviados e a **ciência será concretizada**.

> **Implementação Opcional:** A implementação da **segunda forma** de comunicação é opcional. Os tribunais que não a adotarem deverão assegurar que a consulta do processo pelo órgão destinatário da comunicação **implique a ciência da comunicação**.

---

## Glossário

| Termo | Significado |
|-------|-------------|
| **MNI** | Modelo Nacional de Interoperabilidade |
| **CNJ** | Conselho Nacional de Justiça |
| **WSDL** | Web Services Description Language — linguagem de descrição de serviços web |
| **XSD** | XML Schema Document — documento de esquema XML |
| **ICP-Brasil** | Infraestrutura de Chaves Públicas Brasileira |
| **CNPJ** | Cadastro Nacional de Pessoa Jurídica |
| **CPF** | Cadastro de Pessoa Física |
| **TPU** | Tabela Processual Unificada (CNJ) |
| **TNU** | Tabela Nacional Unificada |
| **OAB** | Ordem dos Advogados do Brasil |
| **MP** | Ministério Público |
| **AGU** | Advocacia-Geral da União |
| **ANTT** | Agência Nacional de Transportes Terrestres |
| **EC** | Emenda Constitucional |
| **SHA-1** | Secure Hash Algorithm 1 — algoritmo de hash criptográfico |
| **base64Binary** | Formato de codificação binária em base 64 |
| **hexBinary** | Formato de codificação binária em hexadecimal |
| **TCOT** | Termo de Cooperação Técnica |
| **TAC** | Termo de Acordo de Cooperação |
| **IBGE** | Instituto Brasileiro de Geografia e Estatística |

---

## Referências Normativas

| Referência | Descrição |
|------------|-----------|
| **Resolução CNJ 46** | Tabelas Nacionais Unificadas (TNUs) — Define os códigos nacionais de tipos de documentos |
| **Resolução CNJ 65** | Numeração única de processos no Poder Judiciário — Define os campos J, TR e OOOO para identificação de órgãos |
| **Lei n.º 11.419/2006** | Informatização do processo judicial — art. 5.º disciplina os atos de comunicação eletrônicos |
| **EC n.º 45/2004** | Reforma do Judiciário — prevê distribuição eletrônica e imediata de processos |
| **TCOT n.º 073/2009** | Termo de Cooperação Técnica — base para o sistema processual referenciado |
| **TAC n.º 58/2009** | Termo de Acordo de Cooperação — base para o modelo de interoperabilidade |

---

*Documento gerado a partir do PDF original: `interoperabilidade_2.2.2.pdf`*  
*Fonte: Conselho Nacional de Justiça (CNJ) — Julho de 2014*
