# Relatório de Webscraping — PJe1g Consulta Pública TRF1

> **Data da análise:** 02/03/2026  
> **URL base:** `https://pje1g-consultapublica.trf1.jus.br/consultapublica/`  
> **OAB consultada:** CE 50784 (Amanda Alves de Sousa)  
> **Resultado:** 7 processos encontrados

---

## 1. Visão Geral da Arquitetura do Sistema

O sistema é construído em **JBoss Seam + RichFaces (JSF)** — um framework Java EE legado. Isso implica:

- **Formulários**: todos os envios de dados são via POST com parâmetros JSF (`javax.faces.ViewState`)
- **Links "javascript:void()"**: não são links reais, são triggers de formulários JSF ocultos
- **Tokens de sessão (`ca`)**: cada ação gera um token criptográfico de sessão que expira
- **Cookies de sessão**: gerenciados via `JSESSIONID` — obrigatório manter entre requests
- **Select2**: alguns dropdowns (ex: UF) usam a biblioteca Select2 sobre `<select>` do JSF

---

## 2. Fluxo Completo de Navegação

```
[1] GET listView.seam             → Tela de busca inicial
       ↓ preenche OAB + UF + clica Pesquisar
[2] POST listView.seam            → Lista de processos (7 resultados)
       ↓ clica "Ver detalhes"
[3] GET/POST → DetalheProcesso/listView.seam?ca={TOKEN}
                                  → Página de detalhe do processo
       ↓ clica "Visualizar documentos"
[4] GET documentoSemLoginHTML.seam?ca={DOC_TOKEN}&idProcessoDoc={ID}
                                  → Visualizador HTML do documento
       ↓ clica "Gerar PDF"
[5] POST documentoSemLoginHTML.seam?ca={DOC_TOKEN}&idProcessoDoc={ID}
       Body: j_id43:downloadPDF
                                  → Download do PDF
```

---

## 3. Endpoints Identificados

### 3.1 Consulta Pública (Busca)

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/consultapublica/ConsultaPublica/listView.seam` | GET | Carregar tela de busca |
| `/consultapublica/ConsultaPublica/listView.seam` | POST | Executar pesquisa |

**Parâmetros POST para busca por OAB:**
```
fPP:Decoration:numeroOAB           = 50784
fPP:Decoration:letraOAB            = (vazio)
fPP:Decoration:estadoComboOAB      = CE
fPP:pesquisar                      = fPP:pesquisar
javax.faces.ViewState              = {viewState obtido no GET inicial}
```

### 3.2 Detalhe do Processo

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/consultapublica/ConsultaPublica/DetalheProcessoConsultaPublica/listView.seam?ca={TOKEN}` | GET | Página de detalhe |

O `TOKEN` (`ca`) é gerado pelo servidor ao clicar em "Ver detalhes do processo" — é um hash SHA derivado da sessão + processo.

**Exemplo real:**
```
https://pje1g-consultapublica.trf1.jus.br/consultapublica/ConsultaPublica/
  DetalheProcessoConsultaPublica/listView.seam?ca=1e4c20d98e4e97057d4d462afe1ba9e3f12508038c5c97a5
```

### 3.3 Visualizador de Documento (HTML)

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/consultapublica/ConsultaPublica/DetalheProcessoConsultaPublica/documentoSemLoginHTML.seam?ca={DOC_TOKEN}&idProcessoDoc={ID}` | GET | Documento em HTML |

**Exemplo real:**
```
https://pje1g-consultapublica.trf1.jus.br/consultapublica/ConsultaPublica/
  DetalheProcessoConsultaPublica/documentoSemLoginHTML.seam
  ?ca=f20837a76b51af2f129e64fbacc99c8bfba5c4e215d96dd59fe56482e19f53434ab3298c51654e7339298d8653f6de244308234c831cb1f4
  &idProcessoDoc=2238908250
```

**Parâmetros:**
- `ca`: token de acesso ao documento (diferente do token do processo — gerado ao clicar "Visualizar documentos")
- `idProcessoDoc`: ID numérico do documento no banco de dados

### 3.4 Download de PDF

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| Mesmo URL do visualizador HTML | POST | Download do PDF |

**Body do POST:**
```
j_id43=j_id43
j_id43:downloadPDF=j_id43:downloadPDF
javax.faces.ViewState={VALOR_DO_DOM}   ← muda por sessão (j_id3, j_id5...), sempre ler do DOM
ca={DOC_TOKEN}
idProcessoDoc={ID}
```

> ✅ `j_id43` e `j_id43:downloadPDF` são **fixos** entre sessões (verificado).
> ❌ `javax.faces.ViewState` muda — ler com `input[name="javax.faces.ViewState"]`.

**Headers necessários:**
```
Content-Type: application/x-www-form-urlencoded
Referer: {URL do visualizador HTML}
Cookie: JSESSIONID={session_id}
```

### 3.5 Estabilidade dos IDs entre Sessões (verificado experimentalmente)

| Identificador | Comportamento | Observação |
|---|---|---|
| `fPP:Decoration:numeroOAB` | ✅ **Fixo** | Hardcoded no template JSF |
| `fPP:Decoration:estadoComboOAB` | ✅ **Fixo** | Hardcoded; opções são índices 0–26 (CE=5) |
| `fPP:searchProcessos` | ✅ **Fixo** | Botão de busca |
| `j_id43` (form do documento) | ✅ **Fixo** | Mesmo em sessões diferentes |
| `j_id43:downloadPDF` (botão PDF) | ✅ **Fixo** | Mesmo em sessões diferentes |
| `javax.faces.ViewState` | ⚠️ **Muda** | Padrão `j_id{N}` — sempre ler do DOM antes de submeter |
| `ca` do processo (detalhe) | ✅ **Fixo por processo** | Hash determinístico baseado nos dados do processo — igual entre sessões |
| `ca` do documento (viewer) | ❌ **Muda por sessão** | Gerado dinamicamente ao clicar — deve ser extraído do `onclick` do link ou da URL da nova aba |
| `idProcessoDoc` | ✅ **Fixo** | ID numérico do documento no banco — permanente |

> **Conclusão:** os IDs de formulário (`j_id43`, `fPP:*`) são seguros para hardcode no scraper. Apenas o `ca` do documento e o `ViewState` precisam ser capturados dinamicamente da página.

### 3.7 Consulta de Documento por ID (alternativo)

```
https://pje1g-consultapublica.trf1.jus.br:443/consultapublica/Processo/ConsultaDocumento/listView.seam
```
Este endpoint permite consultar um documento diretamente pelo ID sem precisar navegar pelo processo.

---

## 4. Estrutura de Dados Extraídos

### 4.1 Lista de Processos (página de resultados)

| Campo | Seletor HTML | Exemplo |
|-------|-------------|---------|
| Número do processo | texto do link na coluna "Processo" | `MSCiv 1013264-53.2025.4.01.3904` |
| Número CNJ | parte do texto do link | `1013264-53.2025.4.01.3904` |
| Classe judicial | texto antes do link | `MANDADO DE SEGURANÇA CÍVEL` |
| Assunto | parte do texto do link | `Exame da Ordem OAB` |
| Polo ativo | texto da célula | `FABIO JUNIOR SANTOS REGO` |
| Polo passivo | texto da célula | `PRESIDENTE CONSELHO FEDERAL...` |
| Última movimentação | 3ª célula da linha | `Conclusos para julgamento (24/02/2026 10:30:31)` |
| Token `ca` | href do link "Ver detalhes" (via JS form) | extraído via Playwright |
| URL de detalhes | construída após click | `listView.seam?ca={TOKEN}` |

**7 processos encontrados para OAB CE 50784:**

| Número CNJ | Assunto | Última Movimentação |
|-----------|---------|---------------------|
| 1013264-53.2025.4.01.3904 | Exame da Ordem OAB | Conclusos para julgamento (24/02/2026) |
| 1014980-12.2025.4.01.4100 | Anulação e Correção de Provas / Questões | Conclusos para julgamento (11/02/2026) |
| 1089764-32.2025.4.01.3300 | Anulação e Correção de Provas / Questões | Decorrido prazo (23/01/2026) |
| 1098298-53.2025.4.01.3400 | Exame da Ordem OAB | Juntada de apelação (13/02/2026) |
| 1000511-48.2026.4.01.3704 | Anulação e Correção de Provas / Questões | Cancelada a Distribuição (02/02/2026) |
| 1000589-45.2026.4.01.3315 | Anulação e Correção de Provas / Questões | Juntada de petição intercorrente (23/02/2026) |
| 1000654-37.2026.4.01.3704 | Anulação e Correção de Provas / Questões | Conclusos para decisão (02/02/2026) |

### 4.2 Dados do Processo (página de detalhe)

Processo inspecionado: **1013264-53.2025.4.01.3904**

| Campo | Valor |
|-------|-------|
| Número Processo | 1013264-53.2025.4.01.3904 |
| Data da Distribuição | 04/12/2025 |
| Classe Judicial | MANDADO DE SEGURANÇA CÍVEL (120) |
| Assunto | DIREITO ADMINISTRATIVO - Conselhos Regionais - Exame da Ordem OAB |
| Jurisdição | Subseção Judiciária de Castanhal-PA |
| Órgão Julgador | Vara Federal Cível e Criminal da SSJ de Castanhal-PA |
| Polo Ativo | FABIO JUNIOR SANTOS REGO (IMPETRANTE), AMANDA ALVES DE SOUSA OAB CE50784 (ADVOGADO) |
| Polo Passivo | PRESIDENTE CFG OAB, PRESIDENTE FGV, OAB CONSELHO FEDERAL, FGV |
| Outros Interessados | MINISTÉRIO PÚBLICO FEDERAL (FISCAL DA LEI) |
| Movimentações | 30 registros (2 páginas) |
| Documentos Juntados | 2 documentos (Ato ordinatório + Despacho) |

### 4.3 Movimentações do Processo

Cada linha contém:
- **Data/hora + Descrição do movimento** (coluna "Movimento")
- **Link para documento** vinculado (coluna "Documento") — presente apenas quando há peça juntada

Paginação: 15 itens/página (2 páginas para este processo = 30 movimentações)

### 4.4 Documentos Juntados

Tabela "Documentos juntados ao processo" com 2 colunas:
- **Documento**: link "Visualizar documentos" + data/hora + tipo
- **Certidão**: link "Visualizar documentos" (certidão associada quando houver)

Cada documento possui:
- `idProcessoDoc`: ID numérico único do documento
- `ca` token: gerado ao clicar — é o token de acesso ao documento específico
- Tipo: Ato ordinatório, Despacho, Petição, etc.

**Documento examinado:** `idProcessoDoc=2238908250`
- Conteúdo: ATO ORDINATÓRIO — intimação do MPF para parecer (Portaria 002/2019)
- Assinante: JORGE CLEITON PEREIRA SOARES (23/02/2026 10:33:48)
- Código de verificação: `26022310302372600002155002413`

---

## 5. Estratégia de Webscraping

### Abordagem Recomendada: Playwright (Python)

Dado que o sistema usa JSF com:
- Links via `javascript:void()` que disparam form submissions
- Tokens `ca` gerados dinamicamente a cada ação
- Select2 dropdowns
- Paginação JSF

A abordagem mais confiável é **Playwright** com navegador headless, que lida com tudo isso de forma transparente.

### 5.1 Algoritmo Principal

```python
async def scrape_processos_oab(oab_numero: str, oab_estado: str):
    # 1. Inicializar browser
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        # 2. Navegar para consulta pública
        await page.goto("https://pje1g-consultapublica.trf1.jus.br/consultapublica/ConsultaPublica/listView.seam")
        
        # 3. Preencher número OAB
        await page.fill('input[id*="numeroOAB"]', oab_numero)
        
        # 4. Selecionar estado (Select2)
        oab_uf_select = page.locator('[id*="estadoComboOAB"]')
        await oab_uf_select.click()
        await page.click(f'li.select2-results__option:has-text("{oab_estado}")')
        
        # 5. Clicar Pesquisar e aguardar resultados
        await page.click('button:has-text("Pesquisar")')
        await page.wait_for_selector('table tbody tr', timeout=15000)
        
        # 6. Extrair lista de processos
        processos = await extrair_lista_processos(page)
        
        # 7. Para cada processo, abrir detalhes
        todos_dados = []
        for processo in processos:
            dados = await detalhar_processo(context, page, processo)
            todos_dados.append(dados)
        
        return todos_dados
```

### 5.2 Extração da Lista de Processos

```python
async def extrair_lista_processos(page) -> list[dict]:
    processos = []
    
    # Aguardar a tabela de resultados
    await page.wait_for_selector('tbody tr', timeout=10000)
    linhas = await page.query_selector_all('tbody tr')
    
    for linha in linhas:
        try:
            # Link "Ver detalhes do processo"
            link_detalhe = await linha.query_selector('a:has-text("Ver detalhes")')
            if not link_detalhe:
                continue
            
            # Número e descrição do processo
            celula_processo = await linha.query_selector_all('td')
            if len(celula_processo) < 2:
                continue
            
            texto_processo = await celula_processo[1].inner_text()
            ultima_mov = await celula_processo[2].inner_text() if len(celula_processo) > 2 else ""
            
            # Extrair número CNJ via regex
            import re
            num_match = re.search(r'(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})', texto_processo)
            numero_cnj = num_match.group(1) if num_match else ""
            
            processos.append({
                "numero_cnj": numero_cnj,
                "texto_completo": texto_processo.strip(),
                "ultima_movimentacao": ultima_mov.strip(),
                "link_detalhe_element": link_detalhe,  # guardar referência para click
            })
        except Exception as e:
            print(f"Erro ao extrair linha: {e}")
            continue
    
    return processos
```

### 5.3 Detalhar Processo

```python
async def detalhar_processo(context, page_lista, processo_info: dict) -> dict:
    # Preparar para capturar nova aba que abre ao clicar "Ver detalhes"
    async with context.expect_page() as new_page_info:
        await processo_info["link_detalhe_element"].click()
    
    detail_page = await new_page_info.value
    await detail_page.wait_for_load_state("networkidle")
    
    dados = {}
    
    # Extrair dados básicos do processo
    dados["numero"] = await _texto_safe(detail_page, '[id*="numeroProcesso"]')
    dados["data_distribuicao"] = await _texto_safe(detail_page, 'td:has-text("Data da Distribuição") + td')
    dados["classe_judicial"] = await _texto_safe(detail_page, 'td:has-text("Classe Judicial") + td')
    dados["assunto"] = await _texto_safe(detail_page, 'td:has-text("Assunto") + td')
    dados["jurisdicao"] = await _texto_safe(detail_page, 'td:has-text("Jurisdição") + td')
    dados["orgao_julgador"] = await _texto_safe(detail_page, 'td:has-text("Órgão Julgador")')
    
    # Polo ativo
    dados["polo_ativo"] = await extrair_polo(detail_page, "Polo ativo")
    
    # Polo passivo
    dados["polo_passivo"] = await extrair_polo(detail_page, "Polo Passivo")
    
    # Movimentações (com paginação)
    dados["movimentacoes"] = await extrair_movimentacoes_paginadas(detail_page)
    
    # Documentos juntados
    dados["documentos"] = await extrair_documentos(context, detail_page)
    
    await detail_page.close()
    return dados
```

### 5.4 Extrair Movimentações com Paginação

```python
async def extrair_movimentacoes_paginadas(page) -> list[dict]:
    movimentacoes = []
    
    while True:
        # Extrair movimentações da página atual
        linhas = await page.query_selector_all('div:has(h3:has-text("Movimentações")) table tbody tr')
        
        for linha in linhas:
            celulas = await linha.query_selector_all('td')
            if not celulas:
                continue
            
            mov_texto = await celulas[0].inner_text() if len(celulas) > 0 else ""
            doc_texto = await celulas[1].inner_text() if len(celulas) > 1 else ""
            
            # Verificar se há link de documento nesta movimentação
            doc_link = await celulas[1].query_selector('a') if len(celulas) > 1 else None
            
            movimentacoes.append({
                "descricao": mov_texto.strip(),
                "documento_vinculado": doc_texto.strip(),
                "tem_documento": doc_link is not None,
            })
        
        # Verificar se há próxima página
        next_btn = await page.query_selector('a:has-text("Próxima") img, [title="Próxima página"]')
        if not next_btn:
            break
        await next_btn.click()
        await page.wait_for_timeout(1000)
    
    return movimentacoes
```

### 5.5 Extrair e Baixar Documentos

```python
async def extrair_documentos(context, detail_page) -> list[dict]:
    documentos = []
    
    # Selecionar tabela "Documentos juntados ao processo"
    doc_links = await detail_page.query_selector_all(
        'div:has(h3:has-text("Documentos juntados")) a:has-text("Visualizar documentos")'
    )
    
    for doc_link in doc_links:
        try:
            # Capturar nova aba ao clicar "Visualizar documentos"
            async with context.expect_page() as new_page_info:
                await doc_link.click()
            
            doc_page = await new_page_info.value
            await doc_page.wait_for_load_state("networkidle")
            
            # Extrair URL com ca e idProcessoDoc
            doc_url = doc_page.url
            
            # Extrair idProcessoDoc da URL
            import re
            id_match = re.search(r'idProcessoDoc=(\d+)', doc_url)
            ca_match = re.search(r'ca=([a-f0-9]+)', doc_url)
            
            doc_id = id_match.group(1) if id_match else None
            ca_token = ca_match.group(1) if ca_match else None
            
            # Extrair conteúdo HTML do documento
            conteudo_html = await doc_page.inner_html('body')
            conteudo_texto = await doc_page.inner_text('body')
            
            # Baixar o PDF
            pdf_bytes = await baixar_pdf_documento(doc_page, doc_url)
            
            documentos.append({
                "id_processo_doc": doc_id,
                "ca_token": ca_token,
                "url_viewer": doc_url,
                "conteudo_texto": conteudo_texto,
                "pdf_bytes": pdf_bytes,
                "pdf_salvo": f"documento_{doc_id}.pdf",
            })
            
            await doc_page.close()
        except Exception as e:
            print(f"Erro ao extrair documento: {e}")
            continue
    
    return documentos
```

### 5.6 Download do PDF via POST

```python
async def baixar_pdf_documento(doc_page, doc_url: str) -> bytes | None:
    """
    O PDF é gerado por POST JSF ao mesmo URL do visualizador HTML.
    
    O botão "Gerar PDF" está no formulário j_id43 e dispara:
    POST documentoSemLoginHTML.seam?ca=...&idProcessoDoc=...
    Body: j_id43=j_id43&j_id43:downloadPDF=j_id43:downloadPDF&javax.faces.ViewState=j_id3
    """
    try:
        # Aguardar o botão "Gerar PDF" estar presente
        await doc_page.wait_for_selector('a:has-text("Gerar PDF"), button:has-text("Gerar PDF")', timeout=5000)
        
        # Configurar interceptação do download
        async with doc_page.expect_download(timeout=30000) as download_info:
            pdf_btn = doc_page.locator('a:has-text("Gerar PDF")')
            await pdf_btn.click()
        
        download = await download_info.value
        pdf_path = f"/tmp/pje_{download.suggested_filename or 'documento.pdf'}"
        await download.save_as(pdf_path)
        
        with open(pdf_path, 'rb') as f:
            return f.read()
            
    except Exception as e:
        print(f"Erro ao baixar PDF: {e}")
        # Fallback: POST direto com httpx mantendo cookies do Playwright
        return await _baixar_pdf_via_post(doc_page, doc_url)


async def _baixar_pdf_via_post(doc_page, doc_url: str) -> bytes | None:
    """Fallback: POST manual para download de PDF."""
    import httpx
    from urllib.parse import urlparse, parse_qs
    
    # Obter cookies do Playwright
    cookies_list = await doc_page.context.cookies()
    cookies = {c['name']: c['value'] for c in cookies_list}
    
    # Extrair parâmetros da URL
    parsed = urlparse(doc_url)
    
    # Obter ViewState do formulário
    view_state = await doc_page.evaluate(
        "() => document.querySelector('input[name=\"javax.faces.ViewState\"]')?.value"
    )
    
    async with httpx.AsyncClient(cookies=cookies, follow_redirects=True) as client:
        response = await client.post(
            doc_url,
            data={
                "j_id43": "j_id43",                          # FIXO entre sessões ✅
                "j_id43:downloadPDF": "j_id43:downloadPDF",  # FIXO entre sessões ✅
                "javax.faces.ViewState": view_state,          # DINÂMICO — obrigatório ler do DOM ❌
            },
            headers={
                "Referer": doc_url,
                "Content-Type": "application/x-www-form-urlencoded",
            }
        )
        
        if response.status_code == 200 and 'pdf' in response.headers.get('content-type', '').lower():
            return response.content
    
    return None
```

---

## 6. Implementação Completa do Scraper

### 6.1 Estrutura de Arquivos

```
scraper/
  app/
    scrapers/
      pje_trf1/
        __init__.py
        scraper.py          # Scraper principal (Playwright)
        models.py           # Modelos de dados (dataclasses/Pydantic)
        storage.py          # Salvar dados + PDFs
        config.py           # Configurações (OAB, paths, delays)
    workers/
      pje_trf1_worker.py   # Taskiq worker para execução periódica
```

### 6.2 Modelo de Dados

```python
# models.py
from pydantic import BaseModel
from datetime import datetime
from pathlib import Path

class Participante(BaseModel):
    nome: str
    cpf_cnpj: str | None = None
    oab: str | None = None
    papel: str  # IMPETRANTE, ADVOGADO, IMPETRADO, FISCAL DA LEI
    representante: str | None = None
    situacao: str = "Ativo"

class Movimentacao(BaseModel):
    data_hora: datetime
    descricao: str
    documento_vinculado: str | None = None
    tem_documento: bool = False

class Documento(BaseModel):
    id_processo_doc: str
    ca_token: str
    url_viewer: str
    data_hora: datetime
    tipo: str  # Ato ordinatório, Despacho, Petição, etc.
    descricao: str
    conteudo_texto: str | None = None
    pdf_path: Path | None = None

class ProcessoDetalhado(BaseModel):
    numero_cnj: str
    data_distribuicao: str
    classe_judicial: str
    assunto: str
    jurisdicao: str
    orgao_julgador: str
    endereco_orgao: str | None = None
    polo_ativo: list[Participante]
    polo_passivo: list[Participante]
    outros_interessados: list[Participante]
    movimentacoes: list[Movimentacao]
    documentos: list[Documento]
    url_detalhe: str
    ca_token: str
    scraped_at: datetime
```

### 6.3 Configurações e Boas Práticas

```python
# config.py
PJE_CONFIG = {
    "base_url": "https://pje1g-consultapublica.trf1.jus.br/consultapublica",
    "endpoints": {
        "lista": "/ConsultaPublica/listView.seam",
        "detalhe": "/ConsultaPublica/DetalheProcessoConsultaPublica/listView.seam",
        "documento_html": "/ConsultaPublica/DetalheProcessoConsultaPublica/documentoSemLoginHTML.seam",
        "consulta_doc": "/Processo/ConsultaDocumento/listView.seam",
    },
    "delays": {
        "entre_processos": 2.0,      # segundos entre processos (respeito ao servidor)
        "entre_documentos": 1.5,     # segundos entre documentos
        "timeout_pagina": 30000,     # ms para load da página
        "timeout_download": 60000,   # ms para download de PDF
    },
    "retry": {
        "max_tentativas": 3,
        "backoff_factor": 2,
    },
    "oab": {
        "numero": "50784",
        "estado": "CE",
    },
    "output_dir": "/data/pje_trf1",
}
```

---

## 7. Desafios e Soluções

| Desafio | Solução |
|---------|---------|
| Links são `javascript:void()` | Usar Playwright — simula clique e captura nova aba via `openPopUp()` automaticamente |
| IDs de form (`j_id43`, `fPP:*`) | **São fixos** — verificado em múltiplas sessões, podem ser hardcoded |
| `ca` do processo (detalhe) | **É fixo por processo** — pode ser extraído do `onclick` do link "Ver detalhes" no HTML da lista |
| `ca` do documento (viewer) | **Muda por sessão** — extrair do `onclick` do link "Visualizar documentos" ou da URL da nova aba |
| `javax.faces.ViewState` | **Muda** (padrão `j_id{N}`) — sempre extrair do DOM com `input[name="javax.faces.ViewState"]` |
| Select2 dropdown para UF | O `<select>` HTML real usa índices numéricos (CE=5, SP=25 etc) — setar via JS direto no `<select>` |
| Paginação de movimentações | Detectar botão "Próxima página" e iterar até não existir mais |
| Download de PDF (JSF form POST) | `expect_download()` do Playwright — form `j_id43`, botão `j_id43:downloadPDF` são fixos |
| Rate limiting / CAPTCHA | Adicionar delays aleatórios (2-4s entre requisições), respeitar limites |
| Certificados SSL | `verify=False` temporário para staging, produção precisa do cert bundle do TRF1 |
| Processos com segredo de justiça | Sistema retorna lista vazia — tratar normalmente como "sem resultados" |

---

## 8. Exemplo de Saída Esperada

```json
{
  "oab": "CE50784",
  "advogado": "AMANDA ALVES DE SOUSA",
  "total_processos": 7,
  "processos": [
    {
      "numero_cnj": "1013264-53.2025.4.01.3904",
      "data_distribuicao": "04/12/2025",
      "classe_judicial": "MANDADO DE SEGURANÇA CÍVEL (120)",
      "assunto": "Exame da Ordem OAB (10170)",
      "jurisdicao": "Subseção Judiciária de Castanhal-PA",
      "orgao_julgador": "Vara Federal Cível e Criminal da SSJ de Castanhal-PA",
      "polo_ativo": [
        {"nome": "FABIO JUNIOR SANTOS REGO", "cpf": "995.807.802-34", "papel": "IMPETRANTE"},
        {"nome": "AMANDA ALVES DE SOUSA", "oab": "CE50784", "papel": "ADVOGADO"}
      ],
      "polo_passivo": [
        {"nome": "PRESIDENTE CONSELHO FEDERAL DA OAB", "papel": "IMPETRADO"},
        {"nome": "PRESIDENTE DA FUNDACAO GETULIO VARGAS - FGV", "papel": "IMPETRADO"},
        {"nome": "ORDEM DOS ADVOGADOS DO BRASIL CONSELHO FEDERAL", "cnpj": "33.205.451/0001-14", "papel": "IMPETRADO"},
        {"nome": "FUNDACAO GETULIO VARGAS", "cnpj": "33.641.663/0001-44", "papel": "IMPETRADO"}
      ],
      "outros_interessados": [
        {"nome": "MINISTERIO PUBLICO FEDERAL - MPF", "cnpj": "26.989.715/0001-02", "papel": "FISCAL DA LEI"}
      ],
      "total_movimentacoes": 30,
      "documentos": [
        {
          "id_processo_doc": "2238908250",
          "tipo": "Ato ordinatório",
          "data_hora": "2026-02-23T10:33:48",
          "assinante": "JORGE CLEITON PEREIRA SOARES",
          "conteudo_resumo": "Intimação do MPF para parecer em 10 dias...",
          "pdf_path": "/data/pje_trf1/1013264-53.2025.4.01.3904/2238908250.pdf"
        }
      ],
      "url_detalhe": "https://pje1g-consultapublica.trf1.jus.br/..."
    }
  ]
}
```

---

## 9. Considerações Legais e Éticas

1. **Dados públicos**: O sistema é de **consulta pública** — não requer login. Os dados são destinados à publicidade dos atos processuais (CNJ Resolução 121/2010)
2. **Rate limiting**: Respeitar delays mínimos de 2-3 segundos entre requisições para não sobrecarregar o servidor
3. **Robots.txt**: Verificar e respeitar: `https://pje1g-consultapublica.trf1.jus.br/robots.txt`
4. **LGPD**: CPFs parcialmente ofuscados ao armazenar (ex: `995.8**.***-34`)
5. **Processos sob segredo**: O sistema não retorna esses casos — o scraper não precisa fazer nada especial
6. **Não usar para fins comerciais sem autorização do TRF1**

---

## 10. Dependências Python Necessárias

```toml
# pyproject.toml additions
[tool.poetry.dependencies]
playwright = "^1.44"
httpx = "^0.27"
beautifulsoup4 = "^4.12"
lxml = "^5.2"
pydantic = "^2.7"

# playwright browser install
# poetry run playwright install chromium
```

---

*Relatório gerado via análise direta do sistema PJe1g TRF1 com Playwright em 02/03/2026*
