# Modelo Nacional de Interoperabilidade (MNI) 2.2.2 - Fonte da Verdade Consolidada

**Conselho Nacional de Justiça — CNJ**  
**Versão:** 2.2.2 (Referência de Julho de 2014)  
**Base:** Este documento consolida as especificações técnicas formais do CNJ e as orientações práticas de implementação, atuando como a única fonte da verdade para o uso do intercâmbio de dados judiciais (foco especial em Consulta e Cadastro de Processos).

---

## Sumário
1. [Contextualização e Visão Geral](#1-contextualizacao-e-visao-geral)
2. [Autenticação e Autorização (Sigilo)](#2-autenticacao-e-autorizacao-sigilo)
3. [Mudanças Significativas na Versão 2.2.2](#3-mudancas-significativas-na-versao-222)
4. [Arquivos e Visão Geral dos Objetos (XSD)](#4-arquivos-e-visao-geral-dos-objetos-xsd)
5. [Tipos e Entidades do Domínio de Dados Detalhado](#5-tipos-e-entidades-do-dominio-de-dados-detalhado)
6. [Visão Geral dos Serviços e Operações Ofertadas](#6-visao-geral-dos-servicos-e-operacoes-ofertadas)
7. [Detalhamento Prático das Operações Principais](#7-detalhamento-pratico-das-operacoes-principais)
8. [Dinâmica das Comunicações e Regras de Negócio](#8-dinamica-das-comunicacoes-e-regras-de-negocio)
9. [Glossário e Referências Normativas](#9-glossario-e-referencias-normativas)

---

## 1. Contextualização e Visão Geral
Este modelo estabelece as bases para o **intercâmbio de informações de processos judiciais e assemelhados** entre os diversos órgãos de administração da Justiça. Foi estruturado para viabilizar sistemas processuais pautados no Termo de Cooperação Técnica **TCOT n.º 073/2009** e no Acordo **TAC n.º 58/2009**.

A definição clara dos elementos de comunicação (*XSD - XML Schema Document*) é determinante para evitar ambiguidades e garantir integração independente das tecnologias usadas por cada provedor. O serviço baseia-se em Web Services **SOAP** descritos por um **WSDL** originário.

---

## 2. Autenticação e Autorização (Sigilo)

### 2.1 Autenticação Base
O meio **preferencial** de autenticação nos endpoints do MNI é por **canal seguro com autenticação mútua via certificado digital cliente** (mTLS de formato ICP-Brasil, e-CNPJ ou e-CPF do advogado/ente judicial).
A partir desse certificado, obtém-se o identificador unívoco do cliente ou tribunal para legitimar o acesso. Quando ocorre a autenticação mTLS, os parâmetros estruturais dos métodos XML (como `idConsultante`, `senhaConsultante`, `idManifestante`, etc.) são costumeiramente ignorados pelo tribunal receptor.

**Autenticação Alternativa:** Caso não haja mTLS possível na ponta, a comunicação deverá ser em canal **HTTPS**, autenticando efetivamente via objeto com inserção de **login/senha** ou `idConsultante/idManifestante`. Para a comunicação entre tribunais, a identificação se constitui dos campos "J", "TR", e "OOOO" ditados pela Resolução CNJ 65.

### 2.2 Autorização e Níveis de Sigilo
O controle de acesso a retornos obedece estritamente às premissas de **nível de sigilo**. Cabe aos sistemas clientes respeitar esses limites ao repassar e manusear os retornos:

| Nível | Nome | Acesso Liberado para |
|:---:|:---|:---|
| **0** | **Público** | Todos servidores judiciários, órgãos públicos cooperadores, advogados e generalistas. |
| **1** | **Segredo** | Servidores judiciários, órgãos rep., e às **partes do processo** (inclusive advogados constituídos). |
| **2** | **Sigilo Mínimo** | Servidores judiciários e aos demais órgãos públicos de colaboração na administração da Justiça. |
| **3** | **Sigilo Médio** | Servidores do órgão onde tramita, partes que originaram o incidente e expressamente incluídos. |
| **4** | **Sigilo Intenso** | Classes de servidores qualificadas (Magistrados, Diretores, Assessores), e partes referendadas. |
| **5** | **Sigilo Absoluto** | **Apenas o magistrado** do órgão pertinente, servidores por ele indicados e partes autorizadas. |

*O tribunal implementador deve adequar seus "segredos internos" para os níveis mais rigorosos equivalentes dessa taxonomia.*

---

## 3. Mudanças Significativas na Versão 2.2.2
Avanços em relação à 2.1.1 para atenção dos integradores:

* **Novas Operações e Respostas:** Inserida a operação `confirmarRecebimento` (com entrada `tipoConfirmarRecebimento` e saída `tipoConfirmarRecebimentoResposta`) para que os tribunais que recebem volumes atestem ao receptor a intersecção total da remessa.
* **Consulta de Processo:** O método `tipoConsultarProcesso` acrescentou `<incluirCabecalho>` (boolean) permitindo omitir a estrutura da capa inicial, economizando bandwidth caso só os XML dos movimentos sejam necessários.
* **`tipoNumeroUnico`:** A restrição regex foi relaxada linearmente para `\d{20}`.
* **`modalidadeVinculacaoProcesso`:** Adoção dos códigos: `AR` (Ação Rescisória), `CD` (Competência Delegada), `RR` (Recurso Repetitivo) e `RG` (Repercussão Geral).
* **`tipoParte`:** Nó de ente estatal foi refatorado de `<interesse-publico>` para **`<interessePublico>`** com fins de adequação de formatação camelCase.
* **`tipoCabecalhoProcesso`:** O atributo `codigoOrgaoJulgador` foi extinto e suprimido. Em sua vez, nasceu o nó obrigatório `<orgaoJulgador>` (do novo tipo `tipoOrgaoJulgador`). Inclusão do atributo `<dataAjuizamento>` na capa, bem como acréscimo de eventuais `<outrosNumeros>`.
* **`tipoMovimentoProcessual`:** `movimentoLocal` transitou de `String` genérico para o complexo e minucioso `tipoMovimentoLocal`.
* **`tipoDocumento`:** Nó vital. Seu anexo matriz migrou decodificação em `<conteudo>` de `hexBinary` para a versão atual universal padrão API de **`base64Binary`** (`application/octet-stream`). A obrigatoriedade conceitual passa a exigir o Código Nacional de classes e templates catalogado na Resolução CNJ 46. Foram abertos para documentação os opcionais `descricao` e `tipoDocumentoLocal`.
* **`tipoAssinatura`:** Adicionada `dataAssinatura` em formato full `tipoDataHora`. Agora é comportado também o array de `<tipoSignatarioSimples>` com o intuito de abrigar assinantes em coautoria eletrônica.
* **`tipoEntregarManifestacaoResposta`:** Recibo (comprovante) transacionado pela base convertida a em `base64Binary`.

---

## 4. Arquivos e Visão Geral dos Objetos (XSD)
Para que seja estagnada as confusões de implementação cliente, toda serialização de XML provém de dois escopos documentados:

### 4.1 Schema Base: `Intercomunicacao-2.2.2.xsd`
Responsável pela modelagem crua e real das entidades subjacentes processuais. Namespace canônico: `http://www.cnj.jus.br/intercomunicacao-2.2.2`. Representa o "Model".
Contém destaques fulcrais: `tipoProcessoJudicial` (processo completo agrupado), `tipoCabecalhoProcesso`, `tipoParte`, `tipoDocumento`, `tipoPessoa`, `tipoOrgaoJulgador`, `tipoMovimentoProcessual`, `tipoMovimentoNacional`, e `tipoEndereco`.

### 4.2 Schema Serviços: `Tipos-servico-intercomunicacao-2.2.2.xsd`
Responsável pela definição envelopante das requisições e retornos SOAP (input/response parameters). Encapsula as entidades do Schema anterior formatando as Request e Replies em rotas operacionais. Namespace: `http://www.cnj.jus.br/tipos-servico-intercomunicacao-2.2.2`.
Abarca formatações tipadas para `tipoConsultaProcesso`, `tipoConfirmarRecebimentoResposta`, e demais envelopes que serão abordados na Seção 6.

---

## 5. Tipos e Entidades do Domínio de Dados Detalhado

As entidades mandatórias de negócios injetáveis e extraíveis comumente ao manipular MNI.

### 5.1 Processo Judicial (`tipoProcessoJudicial`)
A classe raiz englobadora de um processo quando retornado.
* `dadosBasicos` (`tipoCabecalhoProcesso`): A capa oficial.
* `movimento` (`tipoMovimentoProcessual`): Linha cronológica de andamentos (lista).
* `documento` (`tipoDocumento`): Lista de anexos / PDFs processualísticos e peças encartadas.

### 5.2 Cabeçalho / Capa (`tipoCabecalhoProcesso`)
Mergulho e requisito obrigatório ao requerer submissão (Inicial ou Remessa) como `<choice>` `dadosBasicos`.
* **Atributos Principais:** `numero` (Na injeção de novos preenche-se com uma matriz neutra, p.ex., `00000000000000000000`; porém devolução na consulta expõe o NPU oficial `\d{20}`), `classeProcessual` (Código Resolução 46), `codigoLocalidade` (fórum/comarca de competência no envio), `nivelSigilo` (0-5). Parâmetros menores abrangem o facultativo `competencia`, `intervencaoMP`, `dataAjuizamento`.
* **Elementos Filhos:**
    * `polo` (`tipoPoloProcessual`): Definições de Ativo/Passivo.
    * `assunto` (`tipoAssuntoProcessual`): Temas de debate atrelados à inicial.
    * `orgaoJulgador` (`tipoOrgaoJulgador`): Mandatório. Indica Código do Órgão e Município IBGE.
    * Outros Filhos: `magistradoAtuante`, `prioridade`, `valorCausa`, `processoVinculado`.

### 5.3 Elemento Documento (`tipoDocumento`)
Unidade autônoma trafegando as "peças", liminares e atestados do fluxo.
* **Atributos Relevantes:** `tipoDocumento` (Token alfabético padrão ou identificador originário, deve ser "INICIAL" nas distribuições embrionárias), `dataHora`, `hash`, `descricao`.
* **Estrutural:**
    * `conteudo`: O nó contendo o codificado em base64Binary, referindo `application/octet-stream`. O PDF efetivo trafega aí.
    * `assinatura` e `documentoVinculado` (Aninha anexos e recibos adjacentes atrelados à mesma peça mãe).

### 5.4 Pólo Processual e Partes (`tipoPoloProcessual`, `tipoParte`, `tipoPessoa`)
* `polo` detém a chave: `AT`: ativo, `PA`: passivo, `TC`: terceiro, `FL`: fiscal lei, `AD`: assistente civil, `VI`: vítima.
* A Parte pode apontar para uma entidade `<pessoa>` estruturada faticamente ou ser aclamado abstract `<interessePublico>` em causas onde não recaem CNPJ explícitos normais. Detém o `advogado` Array respectivo.
* A Pessoa aglutinada detém de praxe `nome`, `numeroDocumentoPrincipal` (CPF-11 ou CNPJ-14), `tipoPessoa` (física, jurídica, autoridade) contendo endereços por CEP.

### 5.5 Assunto do Processo (`tipoAssuntoProcessual`)
Aborda a Taxionomia. Elemento contendo a tag `<codigoNacional>` atestando indexado a TNU CNJ, ou `<assuntoLocal>`. `principal=true` marca flag pilar de recurso representativo do feito perante o trâmite na Distribuição.

---

## 6. Visão Geral dos Serviços e Operações Ofertadas

Composto sobre RPC e trocas de arquivos unificados, com parâmetro único de entrada (`request`) e saída (`response`). Quase em absoluto, o objeto retorno confere os indicativos cruciais genéricos de status da API contendo um booleano de `sucesso` e uma string detalhada repassando eventuais pormenores na tag `mensagem`.

| Operação HTTP/SOAP | Fluxo e Descrição |
|:---|:---|
| **1. `consultarAvisosPendentes`** | Listagem de comunicações/intimações pendentes aguardando ciência. Aceita busca baseada no Identificador Unívoco do causídico ou CPF/CNPJ de Representação. |
| **2. `consultarTeorComunicacao`** | Convalidação do aviso gerado acima. Obtém efetivamente a íntegra atestando "Li e Tomei Ciência", consolidando a data preclusiva nos autos. |
| **3. `consultarProcesso`** | Busca estrutural complexa para capturar o `tipoProcessoJudicial`. Restrito sempre ao nível correspondente de sigilo. Documentos anexados podem se abster de trafegar legíveis para proteger segurança ponta a ponta (ver SHA-1 Regra 8.3). |
| **4. `entregarManifestacaoProcessual`** | Operação de Protocolo / Ajuizamento por Excelência. Hospeda envios de Iniciais originárias bem como Peticionamento de Recursos ou Documentos num processo em andamento. |
| **5. `consultarAlteracao`** | Método leve, operando verificação pontual a respeito de mudanças no andamento processual e hashs modificados. |
| **6. `confirmarRecebimento`** | **(Exclusivo T.2.T)** Usado para garantir formalidade que o Tribunal Destino obteve de fato todos arquivos provenientes do Tribunal Remetente numa passagem. |

---

## 7. Detalhamento Prático das Operações Principais

### 7.1 Consulta de Processo / Download dos Autos (`consultarProcesso`)
| Campo de Input | XSD Type | Obg | Descrição / Regra Prática |
| :--- | :--- | :---: | :--- |
| `numeroProcesso` | `tipoNumeroUnico` | Sim | NPU formatado (20 dígitos sem mascara). |
| `dataReferencia` | `tipoDataHora` | Não | Caso desejado apenas "Mova-me o Delta/Sincronização" processual, envia a base AAAAMMDDHHMMSS prévia. |
| `movimentos` | `boolean` | Não | Retornar lista ou suprimir andamentos judiciais efetuados no sistema. |
| **`<choice>` (Seletor Mutuamente Exclusivo)** | - | Não | É viável opt-in limitador selecionando UM deles:<br> - `incluirCabecalho=true/false`: Retorna metadados capa geral.<br> - `incluirDocumentos=true/false`: Englobar a conversão Base64 imensa (Autos Completos).<br> - `documento`: Passa-se múltiplos nodes Strings indicando `idDocumento`, para baixar 1 PDF especificamente (Baixa Autos Parcial). |

### 7.2 Cadastro, Petição Interlocutória e Ajuizamento Inicial (`entregarManifestacaoProcessual`)
Pilar bi-funcional que se desdobra do zero para Novo Processo, mas subsiste contínuo num NPU ativo para petições diárias incidentais.

| Campo de Input | XSD Type | Obg | Descrição / Regra Prática |
| :--- | :--- | :---: | :--- |
| **`<choice>` central**| - | Sim | DEVE-SE FAZER UM SPLIT LOGICO E ESCOLHER 1 OU 2:<br> - **Forma 1**: `numeroProcesso` (20 dig), caso incida em Ação Existente!<br> - **Forma 2**: `dadosBasicos`. Abre alas ao Protocolo Inicial submetendo toda a capa com autor, classes de matéria penal/cível e fórum com o NPU fictício alocado momentaneamente. |
| `documento` | `tipoDocumento[]` | Sim | Lista massiva contendo anexos base64Binary. (Submissão inicial exige ao menos 1 carimbado "INICIAL"). |
| `dataEnvio` | `tipoDataHora` | Sim | Timestamp para garantia local. |
| `parametros` | `tipoParametro[]` | Não | Pode repassar metadados e contornos como conflito de varas ao Tribunal. |

**Output da Entrega:** Instala objeto `tipoEntregarManifestacaoProcessualResposta`. Confere `<sucesso>`, dita a `<mensagem>`, e garante ao manifestante o `<protocoloRecebimento>` e um robusto objeto `Recibo` assinado criptograficamente nos servicos centrais, certificando os autos.

---

## 8. Dinâmica das Comunicações e Regras de Negócio

### 8.1 Entre Tribunais (Elevação Instancial Ex.: TJ para STJ)
1. **Remetente Originário:** Envia como `entregarManifestacaoProcessual` dados resumíveis de remessa à corte de elevação.
2. **Recebedor / Destino:** Retorna sucesso e envia o seu correspondente "Protocolo / Novo Caso Autuado".
3. **Download Automático:** Destino, empunhando NPU da Base, utiliza proativamente `consultarProcesso` no remetente copiando volume do litígio.
4. **Acuso Final:** Concluído Parsing, o Destino efetiva sua chancela final executando `confirmarRecebimento`. Assegurado tudo isso, na quebra para rebaixamento ("Devolve o Processo para Execução na Comarca de Origem"), inverte a simetria com as mesmas regalias.

### 8.2 Protocolo Inicial em Distribuição Eletrônica (Sistemas Advocatícios e PJe)
* Ao gerar o `dadosBasicos`, o XML indica a `<codigoLocalidade>` pleiteada. Manda pra frente.
* **Manejo de Rejeição de Competência:** Subitamente, se o envio esbarrar num desvio ou reclassificação, ou seja, onde o distribuidor originário não tenha competência em julgar os requisitos do caso (Conflito de Fórum) - o Backend do PJe responderá `<sucesso>false</sucesso>`. O mesmo injetará um array de chaves com o atributo `"competencia"`. Apontará lá na array as alternativas jurisdicionais disponíveis pro robô/sistema reclassificar a denúncia.
* **Segunda Tentativa com Validade Esticada:** Concedeu-se um lapso de sobrevida legal. Até as `23h59m59s` do dia útil subsequente da rejeição, os submissões enfileiradas daquele protocolo rejeitado com o parâmetro especial nomeado: `"protocolo-originario" + a escolha de "competencia"` (não deve alterar o arquivo SHA) valerão sendo sacramentadas *retroagindo* a primeira tentativa mal-sucedida.

### 8.3 Intimações / Citações Judiciárias (Lei n.º 11.419/2006)
Sustenta as citações e avisos das Defensorias e Grandes Escritórios que fazem varredura via WebServices.
O tribunal expõe o arquivo "Aviso Pendente Processual".
1. **Disponibilizando:** A Vara expede a citação. Disponível de 10 dias passivos. Ou consumado de imediato onde se faz efetivamente a consulta.
2. **Métodos de Captação e Leitura:** Ex.: Consulta unívoca usando o CNPJ da Advocacia Geral da União (AGU).
3. **Leitura Indireta de Conforto/Sigilo:** Alguns Tribunais entregam na resposta XML a intimação com os IDs ou arquivos envelopados e *Encriptados Fechados (SHA-1)*, só conferindo ou libertando seu acesso descodificado num passo extra de *Confirmação de Visualização*, formalizando irreversivelmente a preclusão e prazo contados.

---

## 9. Glossário e Referências Normativas
### Termos Tecnológicos
* **MNI:** Modelo Nacional de Interoperabilidade - Estritamente CNJ.
* **WSDL / XSD:** Camadas abstratas clássicas definindo Contratos Operacionais e Modelagem de Esquemas. Web Service Base SOAP.
* **TPU / TNU:** Tabelas Processuais e Nacionais Unificadas (Os dicionários que geram os Int dos Polos a serem preenchidos, Res. CNJ 46).
* **NPU:** Número Processual Único ("O clássico de 20 dígitos" formatado sem hífens internamente).
* **mTLS (ICP-Brasil):** Mutuo-Transport Layer Security englobando atestação binária criptográfica certificando o client no Handshake (CPF ou e-CNPJ digital assinado por Autoridades Registradoras brasileiras em conformidade a chaves públicas).
* **SHA-1 / SHA-256:** Funções Hash computacionais para testar selagem final evitando tamperamento pós Envio à vara.

### Marcos Regulatórios
* **Resolução CNJ 46:** Código genéticos dos elementos de Classe, Fases, etc.
* **Resolução CNJ 65:** Norteia formatação processual (Campos "J", "TR" para descobrir órgãos no NPU - por ex.: `TR = 02` significa Tribunal Regional).
* **Lei n.º 11.419/2006 (Art. 5º):** Princípios constituintes do Domicílio Eletrônico onde as intimações pendentes geram prazo se passivas na plataforma, ou ativadas se confirmadas por cliques.
* **TAC n.º 58/2009 e TCOT n.º 073/2009:** Elementos ancestrais determinando os papéis jurídicos pro Intercâmbio MNI nacional.

---
*Documento consolidado integrando informações técnicas XSD (MNI 2.2.2 Arquitetural Técnico) e informações pragmático/conceituais inter-operações do fluxo processual.*
