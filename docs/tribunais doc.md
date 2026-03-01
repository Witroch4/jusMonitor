Aqui estão os **links diretos e os caminhos oficiais** para as documentações e WSDLs mencionados no seu texto, organizados pela arquitetura do sistema:

### 1. O Padrão Base (CNJ - MNI)

A "bíblia" do protocolo. É aqui que você encontra os XSDs e a especificação dos tipos complexos (`tipoConsultarProcesso`, `tipoEntregarManifestacao`).

* **Portal de Interoperabilidade do CNJ:** [https://www.cnj.jus.br/tecnologia-da-informacao-e-comunicacao/comite-nacional-de-gestao-de-tecnologia-da-informacao-e-comunicacao-do-poder-judiciario/modelo-nacional-de-interoperabilidade/](https://www.cnj.jus.br/tecnologia-da-informacao-e-comunicacao/comite-nacional-de-gestao-de-tecnologia-da-informacao-e-comunicacao-do-poder-judiciario/modelo-nacional-de-interoperabilidade/)
* **Especificação Técnica (PDF e XSDs):** Busque na página pelos arquivos da **Versão 2.2.2** (ainda a mais estável e usada, apesar da existência da 2.2.3 em alguns locais).

### 2. Tribunais Superiores (Documentação Pública)

O STF possui a documentação mais organizada para integração direta.

* **STF (Supremo Tribunal Federal):**
* *Página de Integração:* [Portal de Integração STF - Como se Integrar](https://portal.stf.jus.br/textos/verTexto.asp?servico=processoIntegracaoInformacaoGeral&pagina=ComoSeIntegrarTribunalMNI)
* *Nota:* Esta página confirma os endpoints de Produção (`ws.stf.jus.br`) e Homologação (`wsh.stf.jus.br`) citados no seu relatório.


* **STJ (Superior Tribunal de Justiça):**
* O STJ geralmente exige credenciamento prévio para liberar a documentação técnica do seu barramento de serviços, acessível via **Portal do Desenvolvedor** (requer login após convênio).



### 3. Ecossistema PJe (TRFs, TRTs, TJs)

O PJe tem uma documentação centralizada para a arquitetura, mas cada tribunal tem seu próprio endereço.

* **Documentação Central (Jira/Wiki):** [https://docs.pje.jus.br/](https://docs.pje.jus.br/)
* Aqui você encontra a estrutura do *PJe-Service* e manuais de API.


* **Endpoints Regionais (Exemplos do seu texto):**
* **TRF5:** Geralmente documentado em `https://pje.trf5.jus.br/manual/` ou acessível via descoberta WSDL direta se o IP estiver liberado.
* **TRT7 (CSJT):** Segue o padrão nacional da Justiça do Trabalho. O manual de interoperabilidade do PJe-JT está disponível no portal do **CSJT**.



### 4. Ecossistema e-SAJ (TJSP, TJCE 2º Grau)

A Softplan (desenvolvedora do SAJ) não expõe a documentação de API publicamente de forma tão aberta quanto o PJe.

* **TJSP (Tribunal de Justiça de SP):**
* A documentação técnica detalhada (namespaces específicos como `mni/cda` mencionados no texto) geralmente é entregue aos grandes litigantes (Procuradorias, Defensorias) no momento do convênio.
* *Portal e-SAJ:* [https://esaj.tjsp.jus.br/](https://esaj.tjsp.jus.br/) (A área "Ajuda" ou "Downloads" às vezes contém manuais de integração simplificados).



### 5. Ecossistema eproc (TRF4)

O eproc (nascido no TRF4) tem uma comunidade de desenvolvimento muito ativa e transparente.

* **TRF4 Interoperabilidade:** [https://www.trf4.jus.br/trf4/controlador.php?acao=pagina_visualizar&id_pagina=365](https://www.trf4.jus.br/trf4/controlador.php?acao=pagina_visualizar&id_pagina=365)
* **Wiki/API:** Procure por "API eproc" ou "Webservice eproc" dentro do portal do TRF4. Eles detalham muito bem a separação entre as seções judiciárias (JFRS, JFSC, etc.).

### Resumo para sua Validação (Checklist)

Para validar o sistema descrito no seu relatório, você precisará cruzar as informações destas fontes:

1. **CNJ:** Para a estrutura XML padrão (Envelope SOAP).
2. **Portal STF:** Para validar o fluxo de `ClientHello` e `CertificateVerify` (mTLS).
3. **Docs PJe:** Para confirmar as limitações de tamanho de arquivo (o "teto de vidro" de 5MB/10MB).
4. **Docs TRF4:** Para o roteamento de múltiplos endpoints regionais.

Se precisar, posso ajudar a montar o script Python (`zeep` + `requests` com adaptador `mTLS`) para testar um desses endpoints específicos.