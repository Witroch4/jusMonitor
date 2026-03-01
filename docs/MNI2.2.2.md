# Documentação Técnica: Modelo de Interoperabilidade de Dados do Poder Judiciário (Versão 2.2.2)

## 1. Visão Geral e Contextualização

Este documento estabelece as normas técnicas para o intercâmbio de informações de processos judiciais entre os diversos órgãos de administração da Justiça. O modelo serve como base para a implementação de funcionalidades no sistema processual (TCOT n.º 073/2009) e para a revisão do modelo estabelecido pelo acordo TAC n.º 58/2009.

* 
**Autor:** Conselho Nacional de Justiça (CNJ) 


* 
**Versão:** 2.2.2 


* 
**Data de Publicação:** Julho de 2014 



## 2. Arquitetura de Dados e Objetos

A interoperabilidade baseia-se na definição de objetos de comunicação descritos através de ficheiros XSD (XML Schema Document), permitindo a troca de dados independentemente das implementações locais.

### 2.1. Estrutura dos Ficheiros XSD

O modelo utiliza dois ficheiros principais para definição de esquemas:

1. 
**`Intercomunicacao-2.2.2.xsd`**: Define os objetos básicos para a troca de informações processuais.


* 
**Conteúdo:** Cabeçalhos, movimentos, assuntos, classes, polos, partes, documentos, endereços, etc..


* 
**Objetivo:** Definir tipos básicos reutilizáveis pelos serviços externos.




2. 
**`Tipos-servico-intercomunicacao-2.2.2.xsd`**: Define os elementos utilizados especificamente nas operações dos serviços WEB (input/output).


* 
**Conteúdo:** Encapsula os objetos básicos e adiciona elementos informativos para as operações (ex: `tipoConsultarProcesso`, `tipoEntregaManifestacaoProcessual`).





## 3. Serviços Oferecidos (API)

A comunicação dá-se através de operações definidas num ficheiro WSDL. Todas as operações possuem um parâmetro de entrada e um de saída. As respostas incluem sempre um booleano de sucesso e uma mensagem de texto, além dos dados solicitados.

### 3.1. Lista de Operações Disponíveis

| Operação | Descrição |
| --- | --- |
| **1. consultarAvisosPendentes** | Permite verificar a existência de avisos de comunicação processual pendentes. Pode ser específica (por parte representada) ou genérica (para o órgão de representação, ex: MP, advogados). Retorna uma lista de objetos `tipoAvisoComunicacaoPendente`.

 |
| **2. consultarTeorComunicacao** | Consulta o teor específico de uma comunicação pendente. Retorna objetos `tipoComunicacaoProcessual`.

 |
| **3. consultarProcesso** | Permite a consulta integral a um processo judicial. Retorna um objeto `tipoProcessoJudicial` se o nível de sigilo permitir.

 |
| **4. entregarManifestacaoProcessual** | Destina-se à entrega de manifestações processuais ou petições iniciais. Retorna o número de protocolo, data e recibo em PDF.

 |
| **5. consultarAlteracao** | Verificação rápida quanto à existência de modificações num processo judicial.

 |
| **6. confirmarRecebimento** | **(Nova na v2.2.2)** Exclusiva para comunicação entre tribunais. Permite que o tribunal de destino confirme ao tribunal de origem que recebeu integralmente uma manifestação processual.

 |

## 4. Segurança e Controlo de Acesso

### 4.1. Autenticação

* **Método Preferencial:** Certificados digitais ICP-Brasil. O serviço extrai o CNPJ ou CPF para validação, dispensando login/senha.


* 
**Método Alternativo:** Par login/senha, estritamente sobre canal seguro (HTTPS).


* 
**Entre Tribunais:** Identificação via códigos concatenados (J, TR, OOOO) conforme a Resolução CNJ 65.



### 4.2. Níveis de Sigilo (Autorização)

O acesso aos objetos deve respeitar os seguintes níveis de sigilo:

* **0 (Público):** Acessível a todos, incluindo advogados e órgãos de colaboração.
* **1 (Segredo):** Servidores do Judiciário, órgãos de colaboração e partes do processo (incluindo advogados).
* **2 (Sigilo Mínimo):** Servidores do Judiciário e órgãos de colaboração.
* **3 (Sigilo Médio):** Servidores do tribunal, partes que provocaram o incidente e incluídos expressamente.
* **4 (Sigilo Intenso):** Servidores qualificados (magistrados, assessores), partes do incidente e incluídos expressamente.
* **5 (Sigilo Absoluto):** Apenas magistrados, servidores indicados e partes do incidente.

## 5. Dinâmica das Comunicações

### 5.1. Comunicação Entre Tribunais

O fluxo padrão para remessa de processos ou recursos envolve:

1. 
**Envio:** O tribunal de origem envia dados básicos via `entregarManifestacaoProcessual`.


2. 
**Consulta:** O tribunal de destino, na posse do número do processo, realiza `consultarProcesso` na origem para obter documentos e metadados completos.


3. 
**Confirmação:** Após processar, o tribunal de destino usa `confirmarRecebimento` para sinalizar o sucesso ao tribunal de origem.


4. 
**Acesso Recíproco:** Ambos os tribunais devem garantir a libertação de acesso para consulta dos processos relacionados.



### 5.2. Protocolo Inicial (Petição Inicial)

Para enviar uma petição inicial via `entregarManifestacaoProcessual`:

* O elemento `numeroProcesso` deve ser substituído por um cabeçalho onde o número do processo é uma sequência de 20 zeros.


* **Conflito de Competência:** Se houver erro de distribuição automática, o sistema retorna insucesso com a lista de competências possíveis. O protocolo deve ser retentado indicando a competência correta e o parâmetro `protocolo-originario`.



### 5.3. Avisos de Comunicação (Lei 11.419/2006)

O Judiciário disponibiliza atos de comunicação de forma passiva:

* É gerado um `avisoComunicacaoPendente`.


* O aviso fica disponível por 10 dias ou até à consulta efetiva.


* A consulta é feita pelo identificador (CNPJ/CPF). Ex: A Advocacia-Geral da União pode consultar pelo seu CNPJ (retorna tudo) ou pelo CNPJ de um órgão defendido (ex: ANTT).


* A ciência (consumação da comunicação) ocorre quando se realiza a `consultarTeorComunicacao` ou a consulta do processo com desencriptação dos documentos.



## 6. Registo de Alterações (Versão 2.2.2)

As principais alterações introduzidas nesta versão em relação à 2.1.1 incluem:

### 6.1. Alterações nas Operações

* Inclusão da operação `confirmarRecebimento` e respectivos parâmetros.


* A operação `tipoConsultarProcesso` passou a permitir a não recuperação do cabeçalho processual.



### 6.2. Alterações nos Objetos de Dados

* 
**Vinculação Processual:** Novas modalidades adicionadas: AR (ação rescisória), CD (competência delegada), RR (recurso repetitivo) e RG (repercussão geral).


* 
**Número Único:** Restrição de formato alterada para aceitar apenas `\d{20}` (20 dígitos numéricos).


* **Cabeçalho do Processo:**
* Remoção do atributo `codigoOrgaojulgador`.


* Adição de `dataAjuizamento`, `orgaojulgador` (obrigatório) e `outrosnumeros`.




* **Documentos:**
* Tipo de conteúdo alterado de `hexBinary` para `base64Binary`.


* O atributo `tipoDocumento` exige agora o código nacional (TNU - Resolução CNJ 46).




* 
**Assinatura:** Adicionado suporte para `codificacaoCertificado` e `tipoSignatarioSimples`.

---

# Manual de Integração: Peticionamento Eletrônico via MNI 2.2.2 (Python)

**Autor:** Witalo Rocha (Baseado em documentação oficial CNJ MNI 2.2.2)
**Versão do Protocolo:** MNI 2.2.2 (Padrão Nacional)
**Objetivo:** Desenvolver um cliente de automação (robô) para consulta e envio de petições judiciais sem interface gráfica (browser), utilizando comunicação direta entre servidores (M2M).

---

## 1. Visão Geral e Arquitetura

O sistema baseia-se no **Modelo Nacional de Interoperabilidade (MNI)**. Diferente de automações visuais (Selenium), esta integração troca dados estruturados (XML) via protocolo **SOAP**.

* **Não baixar arquivos:** Você **não** deve baixar os arquivos `.xsd` ou `.wsdl` para a pasta do seu projeto. O cliente Python deve ler o contrato WSDL diretamente da URL do Tribunal em tempo de execução.
* 
**Versão do Protocolo:** Embora exista a versão 3.0, a vasta maioria dos tribunais (TRFs, TJs, TRTs) opera na **versão 2.2.2**.


* 
**Segurança:** A autenticação é feita preferencialmente via **Certificado Digital (A1)** no nível de transporte (mTLS).



---

## 2. Pré-requisitos Técnicos

1. **Linguagem:** Python 3.8+.
2. **Bibliotecas Principais:**
* `zeep`: Para comunicação SOAP.
* `requests`: Para gerenciar a sessão HTTP e certificados.
* `lxml`: Para processamento de XML (dependência do zeep).


3. **Certificado Digital A1:**
* Você deve extrair a *Chave Privada* e o *Certificado Público* do seu arquivo `.pfx`. O Python precisa deles em formato `.pem` (separados ou combinados, mas acessíveis via arquivo).



---

## 3. Mapeamento das Operações (Baseado no PDF MNI 2.2.2)

Conforme o documento oficial, o serviço MNI expõe as seguintes operações principais que seu sistema deve consumir:

### 3.1. Operações Essenciais

| Operação (Nome no Código) | Função Descrita no PDF | Parâmetro de Entrada | Parâmetro de Saída |
| --- | --- | --- | --- |
| `consultarProcesso` | Consulta dados de um processo (capa, partes, movimentos). A implementação deve assegurar o sigilo.

 | `consultarProcesso` | `consultarProcessoResponse` |
| `entregarManifestacaoProcessual` | Envia uma petição (inicial ou incidental). Retorna o protocolo e recibo se bem-sucedido.

 | `entregarManifestacaoProcessual` | `entregarManifestacaoProcessualResposta` |
| `consultarAvisosPendentes` | Verifica se há intimações/citações pendentes para o advogado/ente.

 | `consultarAvisosPendentes` | `consultarAvisosPendentesResposta` |
| `confirmarRecebimento` | <br>**Novo na v2.2.2:** Confirma que um tribunal recebeu integralmente uma remessa.

 | `confirmarRecebimento` | `confirmarRecebimentoResposta` |

### 3.2. Estrutura dos Dados (Tipos Complexos)

Ao montar o seu dicionário de dados no Python para enviar ao `zeep`, atente-se a estas mudanças específicas da versão 2.2.2:

* 
**Binários (PDFs):** O conteúdo do documento (sua petição em PDF) deve ser enviado no formato **`base64Binary`**. *Nota: Na versão anterior era hexBinary, mas na 2.2.2 mudou.*


* 
**Numeração Única:** O campo `numeroProcesso` aceita apenas o formato estrito de 20 dígitos (ex: `12345671220238000000`), sem pontos ou traços.


* 
**Órgão Julgador:** Foi criado um tipo complexo `tipoOrgaoJulgador` que exige o envio do código, nome e instância (ORIG, REV, etc.).



---

## 4. Implementação em Python (Exemplo Prático)

Abaixo, o esqueleto de código validado para conectar usando as definições acima.

```python
from zeep import Client
from zeep.transports import Transport
import requests

# --- CONFIGURAÇÃO ---
# URL do WSDL (Exemplo TRF1 - Mude para o tribunal desejado)
WSDL_URL = 'https://pje1g.trf1.jus.br/pje/intercomunicacao?wsdl'

# Caminhos para seu certificado A1 (Extraídos do .pfx)
CERT_FILE = 'meu_certificado.pem' 
KEY_FILE = 'minha_chave.pem' 

# --- SESSÃO SEGURA (mTLS) ---
# [cite_start]Conforme PDF pág 12: "O meio preferencial para a autenticação... deverá ser a troca de certificados digitais" [cite: 132]
session = requests.Session()
session.cert = (CERT_FILE, KEY_FILE)
session.verify = True # Verifica SSL do tribunal

# Transporte Zeep usando a sessão autenticada
transport = Transport(session=session)

# --- CONEXÃO ---
try:
    # O Zeep baixa o XSD automaticamente aqui. Não precisa ter o arquivo local.
    client = Client(WSDL_URL, transport=transport)
    print(f"Conectado ao serviço MNI 2.2.2 de: {WSDL_URL}")
except Exception as e:
    print(f"Erro de conexão: {e}")
    exit()

# --- EXEMPLO: CONSULTA DE PROCESSO ---
# [cite_start]Estrutura baseada no objeto 'requisicaoConsultarProcesso' [cite: 123]
try:
    resposta = client.service.consultarProcesso(
        idConsultante='12345678900',  # CPF do Advogado (sem pontos)
        senhaConsultante='DUMMY',      # Com certificado, a senha geralmente é ignorada, mas o campo é obrigatório no XSD
        [cite_start]numeroProcesso='00012345620244013800', # 20 dígitos [cite: 44]
        movimentos=True,               # Parâmetro booleano (pode variar levemente por tribunal)
        [cite_start]incluirCabecalho=True          # Novo na v2.2.2 [cite: 76]
    )
    
    if resposta.sucesso:
        print(f"Processo encontrado! Classe: {resposta.processo.dadosBasicos.classeProcessual}")
    else:
        print(f"Erro: {resposta.mensagem}")

except Exception as e:
    print(f"Erro na operação: {e}")

# --- EXEMPLO: PETICIONAMENTO (TEORIA) ---
# [cite_start]Para enviar petição, usa-se 'entregarManifestacaoProcessual' [cite: 123, 130]
# [cite_start]O PDF deve ser convertido para Base64 antes de enviar [cite: 57, 73]

```

---

## 5. Fluxo de Peticionamento (Regras de Negócio)

Para enviar uma petição ("Manifestação Processual"), o PDF define o seguinte fluxo lógico:

1. **Petição Inicial:**
* Você deve usar a operação `entregarManifestacaoProcessual`.
* No campo `numeroProcesso`, você deve preencher com **20 zeros** (`00000000000000000000`) para indicar que é um processo novo.


* O sistema do tribunal fará a distribuição e retornará o número do processo criado.


2. **Petição Incidental (Em processo existente):**
* Usa a mesma operação `entregarManifestacaoProcessual`.
* Preenche o `numeroProcesso` com o número real do processo (20 dígitos).


3. **Resposta (Output):**
* O tribunal retorna um objeto `entregarManifestacaoProcessualResposta`.
* Este objeto contém: `sucesso` (true/false), `mensagem` e, o mais importante, o **Recibo de Protocolo** (um binário PDF em Base64 assinado pelo tribunal).





---

## 6. Níveis de Sigilo

Ao enviar ou consultar documentos, seu sistema deve respeitar os códigos de sigilo definidos na tabela do PDF:

* **0:** Público (Acessível a todos)
* **1:** Segredo de Justiça (Acessível às partes/advogados)
* **2 a 5:** Níveis crescentes de sigilo (Mínimo, Médio, Intenso, Absoluto).

---

## 7. Solução de Problemas Comuns

1. **Erro de Namespace (v3 vs v2):** Se o tribunal retornar erro de XML, verifique se seu `zeep` não está tentando usar definições da v3.0 (que você viu na imagem). Force o uso do WSDL da URL do tribunal, que garantirá o uso da 2.2.2.
2. **Certificado Inválido:** Se houver erro de SSL/TLS handshake, o problema está na extração do `.pfx` para `.pem`. Teste a chave e o certificado separadamente com `openssl`.
3. 
**Tamanho do Arquivo:** O PDF não especifica limite rígido no texto principal, mas menciona ajustes para viabilizar "grandes volumes" na versão 2.2.1. Na prática, a maioria dos tribunais limita cada PDF a 3MB~5MB. Se for maior, você deve quebrar o PDF em partes (Particionamento).

























Integração para os Tribunais

Para permitir integração com o Escritório Digital, os tribunais precisam implementar o MNI (Modelo Nacional de Interoperabilidade) na versão 2.2.2. De início, basta implementar 3 operações: consultarAvisosPendentes, consultarTeorComunicacao e consultarProcesso. A página oficial sobre o Modelo Nacional de Interoperabilidade é: https://www.cnj.jus.br/versoes-anteriores/79275-versao-2-2-2-07-07-2014.

O sistema Escritório Digital é basicamente um sistema que, tendo por referência a arquitetura cliente-servidor, atua como cliente, acessando remotamente a base processual do sistema de processo eletrônico do Tribunal. O passo a passo abaixo explica como efetuar essa integração, de modo a possibilitar que o mesmo esteja habilitado a se integrar com o Escritório Digital:

Implementar as operações consultarAvisosPendentes, consultarTeorComunicacao e consultarProcesso do MNI, de modo a permitir a entrega de comunicações processuais de interesse do advogado, bem como consulta a processos. Uma orientação para essa etapa pode ser encontrada em: https://www.cnj.jus.br/images/dti/Comite_Gestao_TIC/Modelo_Nacional_Interoperabilidade/interoperabilidade_2.2.2.pdf;
Disponibilizar as operações acima num endpoint SOAP, através do acesso ao WSDL do MNI. O WSDL do MNI está disponível em: https://www.cnj.jus.br/images/dti/Comite_Gestao_TIC/Modelo_Nacional_Interoperabilidade/versao_07_07_2014/servico-intercomunicacao-2.2.2.wsdl;
Após a execução do passo 2, é necessário que sejam enviadas para o email g-escritorio.digital@cnj.jus.br as seguintes informações:
a)    Link para acesso ao WSDL do MNI em homologação:
b)    Nome da Unidade Judiciária:
c)    Código da J e TR da Unidade Judiciária, conforme Resolução CNJ nº 65/2008:
d)    Nome do responsável técnico pelo MNI na Unidade Judiciária:
e)    Email do responsável técnico:
f)    Telefone do responsável técnico:
g)    URL MNI de Produção:
h)    Versão MNI de Produção:
i)    Usuário e senha de homologação:
OBS: As informações de usuário e senha de homologação são importantes, pois serão informados no campo idConsultante e senhaConsultante do MNI nos testes que a equipe técnica do CNJ irá efetuar.
É necessário ainda que seja liberado acesso externo para essa instância do MNI em homologação, pois esse caminho será utilizado para efetuar os testes e procedimentos de integração. A equipe de Segurança de TI (ou Redes de Computadores) do Tribunal pode auxiliá-los a respeito;
É importante que as operações MNI implementadas retornem dados exemplos, que podem ser dados arbitrados, ou seja, não é necessário que sejam dados de processos reais. Por exemplo, é necessário que a operação consultarProcesso retorne com sucesso dados de processos informados. Isso também é necessário para os testes de integração;
Quando os passos anteriores, de 1 a 5, tiverem sido completados, o Tribunal receberá usuário e senha de homologação para o sistema Escritório Digital do CNJ. Até essa etapa, nada ainda estará disponível para acesso público;
Sendo aprovada a homologação por parte do Tribunal, e havendo autorização por sua parte, o acesso ao Tribunal por meio do Escritório Digital será finalmente disponibilizado em ambiente público.
Quaisquer dúvidas dos Tribunais sobre a integração com o Escritório Digital podem ser enviadas para o email: g-escritorio.digital@cnj.jus.br