# Peticionamento Inicial PJe TRF1 — Documentação do Fluxo

**Coletado via Playwright MCP em 04/03/2026**
**Tribunal:** TRF1 — `pje1g.trf1.jus.br`
**Processo de referência usado no teste:** `1089764-32.2025.4.01.3300` (MS, SJBA)
**idProcesso criado:** `14112266`

**Status de documentação:**
| STEP | Aba | Status |
|---|---|---|
| 1 | cadastrar.seam | ✅ documentado |
| 2 | tab=assunto | ✅ documentado |
| 3 | tab=parte | ✅ documentado |
| 4 | tab=caracteristica | ✅ documentado |
| 5 | tab=documento | ✅ documentado — PDF uploadado, ASSINAR flow mapeado |
| 6 | tab=protocolar | ✅ documentado — tabela de docs, botão Protocolar, fluxo PJeOffice |

---

## Fluxo Geral

```
1. cadastrar.seam          → Selecionar Matéria + Jurisdição + Classe + clicar Incluir
2. update.seam?tab=assunto → Pesquisar e adicionar assunto(s) ao processo
3. update.seam?tab=parte   → Vincular partes (polo ativo/passivo)
4. update.seam?tab=caracteristica → Características opcionais (segredo, prioridade etc.)
5. update.seam?tab=documento → Incluir petição inicial + documentos
6. update.seam?tab=protocolar → Protocolar (assinar e enviar)
```

---

## STEP 1 — Cadastrar Processo (`cadastrar.seam`)

**URL:** `https://pje1g.trf1.jus.br/pje/Processo/CadastroPeticaoInicial/cadastrar.seam?newInstance=true`

### IDs dos selects (HTML nativo oculto atrás dos widgets RichFaces)

| Campo        | ID do `<select>` nativo |
|-------------|------------------------|
| Matéria      | `processoTrfForm:classeJudicial:j_id207:areaDireitoCombo` |
| Jurisdição   | `processoTrfForm:classeJudicial:jurisdicaoComboDecoration:jurisdicaoCombo` |
| Classe Judicial | `processoTrfForm:classeJudicial:classeJudicialComboDecoration:classeJudicialCombo` |
| Botão Incluir | `processoTrfForm:incluiProcessoButton` |

**"Selecione" value:** `org.jboss.seam.ui.NoSelectionConverter.noSelectionValue`

### Observações técnicas

- Os combos são **widgets RichFaces** com `<select>` HTML nativo escondido
- Para automação: definir `.value` no `<select>` nativo + `dispatchEvent(new Event('change', {bubbles:true}))` aciona o AJAX A4J
- A cadeia é: Matéria → (A4J carrega) → Jurisdição → (A4J carrega) → Classe Judicial
- Após clicar Incluir → redirect para `update.seam?idProcesso=XXXXX&tab=assunto`

### Matérias (TPU/CNJ — iguais em todos os tribunais PJe)

> **Nota:** Matéria é lista do TPU/CNJ. Não muda por tribunal. Já salva em `scraper/app/data/pje_cadastro_dados.py`.

| value | text |
|-------|------|
| 1861 | DIREITO ADMINISTRATIVO E OUTRAS MATÉRIAS DE DIREITO PÚBLICO |
| 2015 | DIREITO AMBIENTAL |
| 3297 | DIREITO ASSISTENCIAL |
| 1137 | DIREITO CIVIL > COISAS |
| 1066 | DIREITO CIVIL > EMPRESAS |
| 915  | DIREITO CIVIL > FAMÍLIA |
| 1061 | DIREITO CIVIL > FATOS JURÍDICOS |
| 954  | DIREITO CIVIL > OBRIGAÇÕES |
| 1108 | DIREITO CIVIL > PESSOAS JURÍDICAS |
| 940  | DIREITO CIVIL > PESSOAS NATURAIS |
| 1125 | DIREITO CIVIL > RESPONSABILIDADE CIVIL |
| 945  | DIREITO CIVIL > SUCESSÕES |
| 1496 | DIREITO DA CRIANÇA E DO ADOLESCENTE |
| 3302 | DIREITO DA SAÚDE |
| 1215 | DIREITO DO CONSUMIDOR |
| 2820 | DIREITO ELEITORAL |
| 1340 | DIREITO INTERNACIONAL |
| 1192 | DIREITO MARÍTIMO |
| 328  | DIREITO PENAL |
| 229  | DIREITO PREVIDENCIÁRIO |
| 1382 | DIREITO PROCESSUAL CIVIL E DO TRABALHO |
| 1266 | DIREITO PROCESSUAL PENAL |
| 2    | DIREITO TRIBUTÁRIO |
| 3560 | DIREITO À EDUCAÇÃO |
| 3221 | QUESTÕES DE ALTA COMPLEXIDADE, GRANDE IMPACTO E REPERCUSSÃO |
| 1365 | REGISTROS PÚBLICOS |

### Jurisdições TRF1 (por tribunal — coletado 04/03/2026)

> **Nota:** Jurisdição é por tribunal. TRF1 completo abaixo.
> **TODO:** Coletar TRF3, TRF5, TRF6, TJCE via rotina de scraping (ver seção "Rotina de Scraping" abaixo).

| value | text |
|-------|------|
| 0  | Núcleos de Justiça 4.0 |
| 1  | Seção Judiciária da Bahia |
| 2  | Seção Judiciária de Goiás |
| 3  | Seção Judiciária de Mato Grosso |
| 4  | Seção Judiciária de Rondônia |
| 5  | Seção Judiciária de Roraima |
| 6  | Seção Judiciária do Acre |
| 7  | Seção Judiciária do Amapá |
| 8  | Seção Judiciária do Amazonas |
| 9  | Seção Judiciária do Distrito Federal |
| 10 | Seção Judiciária do Maranhão |
| 11 | Seção Judiciária do Pará |
| 12 | Seção Judiciária do Piauí |
| 13 | Seção Judiciária do Tocantins |
| 14 | Subseção Judiciária de Alagoinhas-BA |
| 15 | Subseção Judiciária de Altamira-PA |
| 16 | Subseção Judiciária de Anápolis-GO |
| 17 | Subseção Judiciária de Aparecida de Goiânia-GO |
| 18 | Subseção Judiciária de Araguaína-TO |
| 19 | Subseção Judiciária de Bacabal-MA |
| 20 | Subseção Judiciária de Balsas-MA |
| 21 | Subseção Judiciária de Barra do Garças-MT |
| 22 | Subseção Judiciária de Barreiras-BA |
| 23 | Subseção Judiciária de Bom Jesus da Lapa-BA |
| 24 | Subseção Judiciária de Campo Formoso-BA |
| 25 | Subseção Judiciária de Castanhal-PA |
| 26 | Subseção Judiciária de Caxias-MA |
| 27 | Subseção Judiciária de Corrente-PI |
| 28 | Subseção Judiciária de Cruzeiro do Sul-AC |
| 29 | Subseção Judiciária de Cáceres-MT |
| 30 | Subseção Judiciária de Diamantino-MT |
| 31 | Subseção Judiciária de Eunápolis-BA |
| 32 | Subseção Judiciária de Feira de Santana-BA |
| 33 | Subseção Judiciária de Floriano-PI |
| 34 | Subseção Judiciária de Formosa-GO |
| 35 | Subseção Judiciária de Guanambi-BA |
| 36 | Subseção Judiciária de Gurupi-TO |
| 37 | Subseção Judiciária de Ilhéus-BA |
| 38 | Subseção Judiciária de Imperatriz-MA |
| 39 | Subseção Judiciária de Irecê-BA |
| 40 | Subseção Judiciária de Itabuna-BA |
| 41 | Subseção Judiciária de Itaituba-PA |
| 42 | Subseção Judiciária de Itumbiara-GO |
| 43 | Subseção Judiciária de Jataí-GO |
| 44 | Subseção Judiciária de Jequié-BA |
| 45 | Subseção Judiciária de Ji-Paraná-RO |
| 46 | Subseção Judiciária de Juazeiro-BA |
| 47 | Subseção Judiciária de Juína-MT |
| 48 | Subseção Judiciária de Laranjal do Jari-AP |
| 49 | Subseção Judiciária de Luziânia-GO |
| 50 | Subseção Judiciária de Marabá-PA |
| 51 | Subseção Judiciária de Oiapoque-AP |
| 52 | Subseção Judiciária de Paragominas-PA |
| 53 | Subseção Judiciária de Parnaíba-PI |
| 54 | Subseção Judiciária de Paulo Afonso-BA |
| 55 | Subseção Judiciária de Picos-PI |
| 56 | Subseção Judiciária de Redenção-PA |
| 57 | Subseção Judiciária de Rio Verde-GO |
| 58 | Subseção Judiciária de Rondonópolis-MT |
| 59 | Subseção Judiciária de Santarém-PA |
| 60 | Subseção Judiciária de Sinop-MT |
| 61 | Subseção Judiciária de São Raimundo Nonato-PI |
| 62 | Subseção Judiciária de Tabatinga-AM |
| 63 | Subseção Judiciária de Teixeira de Freitas-BA |
| 64 | Subseção Judiciária de Tucuruí-PA |
| 65 | Subseção Judiciária de Uruaçu-GO |
| 66 | Subseção Judiciária de Vilhena-RO |
| 67 | Subseção Judiciária de Vitória da Conquista-BA |

### Rotina de Scraping para Jurisdições (TODO)

> Devemos criar uma rotina no scraper para capturar automaticamente a lista de Jurisdições de cada tribunal.
> O procedimento é:
> 1. Navegar para `cadastrar.seam?newInstance=true` logado
> 2. Selecionar qualquer Matéria (ex: value=`1861`) via `.value` + `dispatchEvent('change')`
> 3. Aguardar o A4J carregar as opções de Jurisdição (~500ms–2s)
> 4. Extrair `Array.from(document.getElementById('...jurisdicaoCombo').options).map(o => ({value: o.value, text: o.text.trim()}))`
> 5. Salvar em `scraper/app/data/pje_cadastro_dados.py` no dict `JURISDICOES[tribunal_code]`
>
> Tribunais pendentes: `trf3`, `trf5`, `trf6`, `tjce`

---

## STEP 2 — Tab Assuntos (`tab=assunto`)

**URL:** `update.seam?idProcesso=14112154&tab=assunto`

**Screenshots:**
- Lista inicial (1749 assuntos): [page-2026-03-04T09-00-15-725Z.png](../.playwright-mcp/page-2026-03-04T09-00-15-725Z.png)
- Após adicionar assunto 10170: [page-2026-03-04T09-03-12-967Z.png](../.playwright-mcp/page-2026-03-04T09-03-12-967Z.png)
- Após adicionar assunto 10379 (2 assuntos finais): [page-2026-03-04T09-06-56-272Z.png](../.playwright-mcp/page-2026-03-04T09-06-56-272Z.png)

### Assuntos adicionados no processo de teste

| Cód. | Assunto (hierarquia completa) |
|------|-------------------------------|
| 10170 | DIREITO ADMINISTRATIVO (9985) > Organização Político-administrativa / Administração Pública (10157) > Conselhos Regionais de Fiscalização Profissional e Afins (10166) > **Exame da Ordem OAB** |
| 10379 | DIREITO ADMINISTRATIVO (9985) > Concurso Público / Edital (10370) > **Anulação e Correção de Provas / Questões** |

### Estrutura da tela

**Painel esquerdo — Assuntos Associados (ao processo)**
- Colunas: (seta →) | Cod. | Assunto Principal (radio) | Assunto | Complementar?
- Inicialmente vazio (0 resultados encontrados)
- A coluna "Assunto Principal" tem um radio button — clicar marca aquele como principal
- A seta → remove o assunto da lista (devolve para resultados)

**Painel direito — Busca + Lista TPU**
- Campo texto "Assunto" — busca por texto livre
- Campo texto "Código" — busca exata por código TPU
- Botão "PESQUISAR" | Botão "LIMPAR"
- Tabela "Assuntos*": total 1749 resultados, paginação (175 páginas de 10)
- Colunas resultados: (seta ←) | Cod. | Assunto | Complementar?
- Clicar na seta ← adiciona o assunto à tabela "Assuntos Associados"

### IDs dos elementos (capturados via JS — 04/03/2026)

| Elemento | ID |
|----------|-----|
| Campo texto "Assunto" | `r_processoAssuntoListSearchForm:j_id4715:j_id4717:assuntoCompleto` |
| Campo texto "Código" | `r_processoAssuntoListSearchForm:j_id4726:j_id4728:codAssuntoTrf` |
| Link Adicionar (seta ← na linha N da lista) | `r_processoAssuntoListList:{N}:j_id4758:j_id4759:j_id4760` |
| Input paginação (página atual) | `j_id4805:j_id4806Input` |

> Nota: os botões "Pesquisar" e "Limpar" não têm ID HTML fixo — localizá-los por texto ou posição no formulário `r_processoAssuntoListSearchForm`.

### Fluxo de automação para adicionar assunto por código

```python
# 1. Limpar campo código e digitar o código desejado
codigo_field = 'r_processoAssuntoListSearchForm:j_id4726:j_id4728:codAssuntoTrf'
page.fill(f'[id="{codigo_field}"]', codigo_tpu)

# 2. Clicar Pesquisar (primeiro button "Pesquisar" visível no form)
page.click('button:has-text("Pesquisar")')
await asyncio.sleep(1)  # aguardar A4J

# 3. Clicar na seta da primeira linha de resultado (row 0)
add_link = 'r_processoAssuntoListList:0:j_id4758:j_id4759:j_id4760'
page.click(f'[id="{add_link}"]')
await asyncio.sleep(1)  # aguardar A4J
```

---

## STEP 3 — Tab Partes (`tab=parte`)

**URL:** `update.seam?idProcesso=14112154&tab=parte`

**Screenshots:**
- Visão geral (3 painéis): [page-2026-03-04T09-04-34-473Z.png](../.playwright-mcp/page-2026-03-04T09-04-34-473Z.png)
- Modal "Associar parte" — Passo 1 (Tipo de Vinculação): [page-2026-03-04T09-08-02-830Z.png](../.playwright-mcp/page-2026-03-04T09-08-02-830Z.png)
- Modal "Associar parte" — Passo 2 (Pré-cadastro com IMPETRADO): [page-2026-03-04T09-08-56-716Z.png](../.playwright-mcp/page-2026-03-04T09-08-56-716Z.png)

### Estrutura da tela

A tela é dividida em 3 painéis (Polo Ativo | Polo Passivo | Outros Participantes).

**Polo Ativo**
- Botões de ação: `[+] Parte` (`id=addParteA`) | `[+] Procurador | Terceiro Vinculado`
- Tabela "Participante" com coluna: (ícone editar/excluir) | Participante
- Pré-populado com o advogado logado: *AMANDA ALVES DE SOUSA - OAB CE50784 - CPF: 070.716.493-16 (ADVOGADO)*
- **Tipos da Parte disponíveis no Polo Ativo:** LITISCONSORTE | TERCEIRO INTERESSADO | ASSISTENTE | **IMPETRANTE**
  - Diferença do Polo Passivo: tem IMPETRANTE em vez de IMPETRADO

**Polo Passivo**
- Botões: `[+] Parte` | `[+] Procurador | Terceiro Vinculado`
- 0 resultados encontrados (vazio — deve adicionar o réu)

**Outros Participantes**
- Botões: `[+] Participante` | `[+] Procurador | Terceiro Vinculado`
- Pré-populado com o MPF: *MINISTERIO PUBLICO FEDERAL - MPF - CNPJ: 26.989.715/0001-02 (FISCAL DA LEI) → Procuradoria da República nos Estados e no Distrito Federal*

### Partes do Processo de Referência (`1089764-32.2025.4.01.3300`)

**Polo Ativo:**
| Parte | CPF/OAB | Tipo | Status |
|-------|---------|------|--------|
| ALEX SILVA MICIO DOS SANTOS | CPF: 677.541.805-10 | IMPETRANTE | ✅ adicionado |
| AMANDA ALVES DE SOUSA | OAB CE50784 | ADVOGADO | ✅ pré-populado (advogado logado) |

**Polo Passivo:**
| Parte | Tipo |
|-------|------|
| ORDEM DOS ADVOGADOS DO BRASIL - CONSELHO FEDERAL | TERCEIRO INTERESSADO |
| PRESIDENTE DO CONSELHO FEDERAL DA OAB | IMPETRADO |
| FUNDAÇÃO GETÚLIO VARGAS - FGV | TERCEIRO INTERESSADO |
| DECIO FLAVIO GONÇALVES AGUIAR | ADVOGADO |
| PRESIDENTE DA FUNDAÇÃO GETÚLIO VARGAS - FGV | IMPETRADO |

**Outros Participantes:**
| Parte | Tipo |
|-------|------|
| MINISTÉRIO PÚBLICO FEDERAL - MPF | FISCAL DA LEI |

### Modal "Associar parte ao processo"

Ao clicar em `[+] Parte` em qualquer polo, abre um modal **inline** com dois passos.

#### Passo 1 — Selecionar Tipo de Vinculação

- Select "Tipo da Parte" é um **widget RichFaces combobox** (não select nativo simples)
- `document.querySelector('select').value = '3'` **NÃO FUNCIONA** — o combobox RichFaces ignora o change event no select interno
- **Solução correta:** clicar no combobox para abrir o dropdown, depois clicar no treeitem desejado

| Opção | Tipo da Parte |
|-------|---------------|
| LITISCONSORTE | treeitem |
| TERCEIRO INTERESSADO | treeitem |
| ASSISTENTE | treeitem |
| IMPETRADO | treeitem |

> **Automação correta:**
> ```python
> # 1. Clicar no combobox "Selecione" para abrir o dropdown
> await page.get_by_role('combobox', name='Selecione').click()
> await asyncio.sleep(0.5)
> # 2. Clicar no treeitem desejado
> await page.get_by_role('treeitem', name='IMPETRADO').click()
> await asyncio.sleep(1)  # aguardar A4J recarregar formulário
> ```

> **ATENÇÃO — `name` do combobox muda a cada abertura do modal.** Localizar sempre por `role=combobox, name='Selecione'` (antes de selecionar) ou por `role=treeitem, name='IMPETRADO'` para a opção.

#### Passo 2 — Pré-cadastro da Pessoa

Após selecionar o tipo, o formulário exibe campos para localizar/cadastrar a pessoa:

| Campo | Tipo | Observações |
|-------|------|-------------|
| Tipo de pessoa | Radio | Física / **Jurídica** (padrão) / Ente ou autoridade |
| Órgão Público? | Radio | **Sim** (padrão) / Não |
| Nome | Textbox | Campo para buscar por nome |
| Botão PESQUISAR | Button | Busca no cadastro PJe |

> **Fluxo completo para adicionar parte:**
> 1. Clicar `[+] Parte` no polo desejado
> 2. Selecionar "Tipo da Parte" via JS no select nativo (`name="j_id11111:j_id11115"`)
> 3. Selecionar "Tipo de pessoa" (Física/Jurídica/Ente ou autoridade)
> 4. Selecionar "Órgão Público?" (Sim/Não)
> 5. Digitar nome no campo texto + clicar PESQUISAR
> 6. Selecionar a pessoa encontrada na lista de resultados
> 7. Confirmar — pessoa vinculada ao polo

> **TODO:** Continuar exploração: capturar IDs exatos dos campos de Pré-cadastro (radio buttons de Tipo de pessoa e Órgão Público, campo Nome, botão Pesquisar, tabela de resultados e botão de seleção).

### IDs dos campos do Pré-cadastro (capturados via JS — 04/03/2026)

| Campo | ID / `name` |
|-------|-------------|
| Tipo de pessoa — Física | `preCadastroPessoaFisicaForm:tipoPessoaDecoration:tipoPessoa:0` (value=`F`) |
| Tipo de pessoa — Jurídica | `preCadastroPessoaFisicaForm:tipoPessoaDecoration:tipoPessoa:1` (value=`J`) |
| Tipo de pessoa — Ente ou autoridade | `preCadastroPessoaFisicaForm:tipoPessoaDecoration:tipoPessoa:2` (value=`A`) |
| Órgão Público — Sim | `preCadastroPessoaFisicaForm:isOrgaoPublico1Decoration:isOrgaoPublico1SelectOneRadio:0` (value=`true`) |
| Órgão Público — Não | `preCadastroPessoaFisicaForm:isOrgaoPublico1Decoration:isOrgaoPublico1SelectOneRadio:1` (value=`false`) |
| Campo Nome (Jurídica) | `preCadastroPessoaFisicaForm:preCadastroPessoaFisica_nomePJDecoration:preCadastroPessoaFisica_nomePJ` |
| Campo Ente ou autoridade | textbox label="Ente ou autoridade" (sem ID fixo — localizar por role+name) |

> **ATENÇÃO — select Tipo da Parte é um RichFaces combobox, não um select nativo.**
> `document.querySelector('select').value = '3'` não funciona.
> Usar: `page.get_by_role('combobox', name='Selecione').click()` → `page.get_by_role('treeitem', name='IMPETRADO').click()`

### Fluxo completo para adicionar parte Jurídica (testado — 04/03/2026)

```python
# 1. Abrir modal "+ Parte" no polo desejado
page.click('#addParteP')  # Polo Passivo — ID: addParteP

# 2. Selecionar Tipo da Parte via combobox RichFaces
await page.get_by_role('combobox', name='Selecione').click()
await asyncio.sleep(0.3)
await page.get_by_role('treeitem', name='TERCEIRO INTERESSADO').click()
# ou: name='IMPETRADO' para IMPETRADO
await asyncio.sleep(1)  # aguardar A4J carregar formulário

# 3. Tipo de pessoa: Jurídica já vem marcado por padrão (value='J')
# 4. Órgão Público: Sim já vem marcado por padrão

# 5. Digitar nome no campo Nome e clicar Pesquisar
# ATENÇÃO: NÃO usar Enter — fecha o modal sem adicionar!
page.fill('[id="preCadastroPessoaFisicaForm:preCadastroPessoaFisica_nomePJDecoration:preCadastroPessoaFisica_nomePJ"]', 'ORDEM DOS ADVOGADOS')
page.click('button:has-text("Pesquisar")')
await asyncio.sleep(1)  # aguardar resultados

# 6. Clicar no radio da linha correta (identificar pelo CNPJ na coluna)
# Tabela: Nome | Tipo de pessoa | CNPJ — clicar no <a> da primeira coluna
# Link da linha N: preCadastroPessoaFisicaForm:orgaoPublicoList:{N}:j_id{X}

# 7. Clicar Inserir (aparece após selecionar)
page.click('button:has-text("Inserir")')
await asyncio.sleep(1)  # aguardar modal fechar e lista atualizar
```

> **Observações importantes:**
> - Busca por CNPJ no campo Nome retorna **0 resultados** — buscar sempre por **nome parcial**
> - Após clicar no radio da linha, aparece seção "Procuradoria: [nome]" e botão **Inserir**
> - Após Inserir, modal fecha e a parte aparece na tabela do polo com ícones: editar | excluir | ação
> - Tipo de pessoa "Ente ou autoridade": exibe apenas campo único "Ente ou autoridade" (sem Órgão Público / Nome separado)

### Fluxo alternativo — Jurídica + Órgão Público = NÃO (busca por CNPJ)

Quando **Tipo de pessoa = Jurídica** e **Órgão Público = Não**, o formulário exibe campo **CNPJ** diretamente:

| Campo | Tipo | Observação |
|-------|------|------------|
| CNPJ* | Textbox | Digitar CNPJ com pontuação (ex: `33.205.451/0001-14`) |
| PESQUISAR / LIMPAR | Buttons | Pesquisar preenche Nome + Nome fantasia automaticamente |
| Não possui este documento | Checkbox | Para empresas sem CNPJ |
| Nome | Textbox (read-only após busca) | Preenchido automaticamente |
| Nome fantasia | Textbox (read-only após busca) | Preenchido automaticamente |
| CONFIRMAR | Button | Confirma adição (diferente de "Inserir" do fluxo Sim) |

> **Diferença dos dois fluxos:**
> - **Órgão Público = Sim** → Campo Nome livre → Pesquisar → tabela de resultados → radio → **Inserir**
> - **Órgão Público = Não** → Campo CNPJ → Pesquisar → auto-preenche Nome → **CONFIRMAR**

Screenshot — modal Jurídica + Órgão Público=Não + CNPJ OAB CF preenchido + Nome auto-preenchido: [page-2026-03-04T09-23-09-335Z.png](../.playwright-mcp/page-2026-03-04T09-23-09-335Z.png)

### 2º Passo — Complementação do cadastro (aparece após CONFIRMAR no fluxo CNPJ)

Após clicar **CONFIRMAR** no fluxo CNPJ, o modal avança para um segundo passo:

```
2º Passo • Complementação do cadastro
├── Tipo da Parte: TERCEIRO INTERESSADO  (select — pode alterar)
├── Tabs: Informações pessoais | Endereços | Meios de contato
├── Razão social da parte no processo  (select "Selecione")
├── Nome de fantasia  (textbox — pré-preenchido com nome da empresa)
├── Tipo de pessoa  (ocultado)
├── Nome do responsável  (ocultado)
├── CPF do responsável  (ocultado)
├── Data de abertura  (ocultado)
├── Data de encerramento de atividades  (textbox)
├── [Salvar]  (botão para salvar dados complementares)
├── Parte sigilosa  (select "Não")
├── Procuradoria  (auto-preenchida — ex: "Procuradoria do Conselho Federal da OAB")
├── [VINCULAR PARTE AO PROCESSO]  ← botão final para vincular
└── [CANCELAR]
```

Screenshot — 2º Passo Complementação do cadastro (OAB CF): [page-2026-03-04T09-23-30-263Z.png](../.playwright-mcp/page-2026-03-04T09-23-30-263Z.png)

> Clicar **VINCULAR PARTE AO PROCESSO** fecha o modal e adiciona a parte ao polo.

Screenshot — Polo Passivo com OAB CF vinculada (fluxo CNPJ): [page-2026-03-04T09-25-23-100Z.png](../.playwright-mcp/page-2026-03-04T09-25-23-100Z.png)

### Screenshots do fluxo de adição de partes

- Pré-cadastro — "Ente ou autoridade" selecionado: [page-2026-03-04T09-13-16-539Z.png](../.playwright-mcp/page-2026-03-04T09-13-16-539Z.png)
- Resultados busca "ORDEM DOS ADVOGADOS" (66 resultados): [page-2026-03-04T09-17-57-786Z.png](../.playwright-mcp/page-2026-03-04T09-17-57-786Z.png)
- OAB CF selecionada + Procuradoria mostrada (pré-Inserir, fluxo Sim): [page-2026-03-04T09-18-09-978Z.png](../.playwright-mcp/page-2026-03-04T09-18-09-978Z.png)
- Polo Passivo com OAB CF (fluxo Sim): [page-2026-03-04T09-18-35-425Z.png](../.playwright-mcp/page-2026-03-04T09-18-35-425Z.png)
- CNPJ OAB CF encontrado + Nome auto-preenchido: [page-2026-03-04T09-23-09-335Z.png](../.playwright-mcp/page-2026-03-04T09-23-09-335Z.png)
- 2º Passo Complementação (pré-VINCULAR): [page-2026-03-04T09-23-30-263Z.png](../.playwright-mcp/page-2026-03-04T09-23-30-263Z.png)
- **Polo Passivo — OAB CF vinculada (fluxo CNPJ, definitivo):** [page-2026-03-04T09-25-23-100Z.png](../.playwright-mcp/page-2026-03-04T09-25-23-100Z.png)

### Fluxo "Ente ou autoridade" — autocomplete

Para **Tipo de pessoa = Ente ou autoridade**, o campo de busca funciona como **autocomplete** (suggest):

```
Campo: "Ente ou autoridade"  (ID: preCadastroPessoaFisicaForm:j_id57454:pessoaAutoridadeSuggest)
maxlength: 50
Tipo: suggest/autocomplete — mostra dropdown ao digitar (não há botão Pesquisar separado)
```

**Fluxo completo:**
1. Selecionar Tipo da Parte (ex: IMPETRADO) via JS `document.querySelector('select')`
2. Clicar radio "Ente ou autoridade"
3. **Digitar `slowly`** no campo → dropdown de sugestões aparece automaticamente
4. Clicar na opção desejada → campo preenche + botão **CONFIRMAR** aparece
5. Clicar **CONFIRMAR** → abre 2º Passo • Complementação do cadastro
   - Mostra: Ente ou autoridade + Órgão vinculado (auto-detectado)
   - Parte sigilosa: Não (padrão)
   - Procuradoria: (vazio para ente/autoridade individual)
6. Clicar **VINCULAR PARTE AO PROCESSO** → parte adicionada ao polo

**Automação (Python/Playwright):**
```python
# 1. Selecionar tipo da parte
await page.evaluate("const s=document.querySelector('select');s.value='3';s.dispatchEvent(new Event('change',{bubbles:true}))")
await asyncio.sleep(1.5)  # aguarda A4J

# 2. Clicar "Ente ou autoridade"
await page.click("[id*='tipoPessoa:2']")
await asyncio.sleep(0.5)

# 3. Digitar lentamente (dispara autocomplete)
field = page.locator("input[id*='pessoaAutoridadeSuggest']")
await field.press_sequentially("PRESIDENTE DO CONSELHO FEDERAL", delay=50)
await asyncio.sleep(1)  # aguarda dropdown

# 4. Clicar primeira opção relevante
await page.click(".rich-suggestion-list tr:nth-child(2)")  # ou localizar por texto

# 5. Confirmar
await page.click("button:has-text('Confirmar')")
await asyncio.sleep(1)

# 6. Vincular
await page.click("button:has-text('Vincular parte ao processo')")
```

> **⚠ ATENÇÃO:** Campo tem `maxlength=50`! Para nomes longos, truncar. O autocomplete retorna sugestões baseado nos primeiros caracteres.

> **Descoberta:** "Ente ou autoridade" NÃO tem botão Pesquisar separado — a busca é inline/autocomplete.
> Não há campo Órgão Público para esse tipo.

Screenshots — Fluxo Ente ou autoridade (IMPETRADO #2):
- Autocomplete com dropdown de sugestões: [page-2026-03-04T09-30-53-966Z.png](../.playwright-mcp/page-2026-03-04T09-30-53-966Z.png)
- 2º Passo após confirmar (Ente + Órgão vinculado): [page-2026-03-04T09-31-18-755Z.png](../.playwright-mcp/page-2026-03-04T09-31-18-755Z.png)
- **Polo Passivo — 2 partes (OAB CF + PRESIDENTE OAB):** [page-2026-03-04T09-31-30-807Z.png](../.playwright-mcp/page-2026-03-04T09-31-30-807Z.png)

### Sequência de adição de partes (processo de referência `1089764-32.2025.4.01.3300`)

> A sequência abaixo é a ordem correta conforme dados informados pelo usuário.
> Deve ser seguida pelo front-end ao automatizar o peticionamento.

**Polo Passivo — ordem de adição:**

| # | Nome no PJe | CNPJ | Tipo da Parte | Tipo de pessoa | Status |
|---|-------------|------|---------------|----------------|--------|
| 1 | ORDEM DOS ADVOGADOS DO BRASIL CONSELHO FEDERAL | 33.205.451/0001-14 | TERCEIRO INTERESSADO | Jurídica (CNPJ) | ✅ adicionado |
| 2 | .PRESIDENTE DO CONSELHO FEDERAL DA ORDEM DOS ADVOGADOS DO BRASIL | — | IMPETRADO | Ente ou autoridade | ✅ adicionado |
| 3 | FUNDACAO GETULIO VARGAS | 33.641.663/0001-44 | TERCEIRO INTERESSADO | Jurídica (CNPJ) | ✅ adicionado |
| 4 | .PRESIDENTE DA FUNDAÇÃO GETÚLIO VARGAS | — | IMPETRADO | Ente ou autoridade | ✅ adicionado |

> **DECIO FLAVIO (ADVOGADO) NÃO é adicionado aqui** — "ADVOGADO" não existe como Tipo da Parte no modal `[+] Parte`. Advogados/representantes são vinculados pelo scraper separadamente via `[+] Procurador | Terceiro Vinculado`.

> **Status: ✅ Tab Partes COMPLETA — 4 resultados no Polo Passivo** | Screenshot: [page-partes-completo.png](../page-partes-completo.png)

Screenshots — Polo Passivo completo (4 partes):
- [page-2026-03-04T09-33-22-072Z.png](../.playwright-mcp/page-2026-03-04T09-33-22-072Z.png) — após #3 (FGV)
- [page-partes-completo.png](../page-partes-completo.png) — **estado final: 4 partes no Polo Passivo**

---

## STEP 4 — Tab Características (`tab=caracteristica`)

**URL:** `update.seam?idProcesso=14112266&tab=caracteristica`

> ✅ **DOCUMENTADO** — 05/03/2026. Todos os IDs PJe extraídos via JS + mapeamento completo com frontend/backend.

### Estrutura da Tela

A aba Características é dividida em **3 formulários independentes**, cada um com seu próprio botão de salvamento:

```
┌──────────────────────────────────────────────────────────┐
│ Formulário 1: formAdicionarCaracteristicasProcesso       │
│  ├── Justiça Gratuita?       (radio Sim/Não)             │
│  ├── Juízo 100% Digital?     (radio Sim/Não)             │
│  ├── Pedido Liminar/Tutela?  (radio Sim/Não)             │
│  ├── Valor da causa (R$)     (text input)                │
│  └── [Salvar]                                            │
├──────────────────────────────────────────────────────────┤
│ Formulário 2: frmSegredoSig                              │
│  ├── Segredo de Justiça      (radio Sim/Não)             │
│  └── [Gravar sigilo]                                     │
├──────────────────────────────────────────────────────────┤
│ Formulário 3: formAddPrioridadeProcesso                  │
│  ├── Prioridade de processo  (select dropdown, 14 opções)│
│  └── [Incluir]  ← repetir para cada prioridade           │
└──────────────────────────────────────────────────────────┘
```

### IDs Completos dos Campos PJe (extraídos via JS — 04/03/2026)

#### Formulário 1 — Características Principais

| Campo | PJe ID (name do radio group) | Sim (suffix) | Não (suffix) | Default |
|-------|------------------------------|--------------|--------------|---------|
| Justiça Gratuita? | `formAdicionarCaracteristicasProcesso:justicaGratuita:justicaGratuitaDecoration:justicaGratuitaSelectOneRadio` | `:0` | `:1` | **Não** |
| Juízo 100% Digital? | `formAdicionarCaracteristicasProcesso:solicitadoJuizo100PorCentoDigital:solicitadoJuizo100PorCentoDigitalDecoration:solicitadoJuizo100PorCentoDigitalSelectOneRadio` | `:0` | `:1` | **Nenhum** |
| Pedido Liminar/Tutela? | `formAdicionarCaracteristicasProcesso:tutelaLiminar:tutelaLiminarDecoration:tutelaLiminarSelectOneRadio` | `:0` | `:1` | **Não** |

| Campo | PJe ID | Tipo | Default |
|-------|--------|------|---------|
| Valor da Causa (R$) | `formAdicionarCaracteristicasProcesso:valorCausa:valorCausaDecoration:valorCausa` | `text` | vazio |
| Botão Salvar | `formAdicionarCaracteristicasProcesso:salvaCaracteristicaProcessoButton` | `button` | — |

#### Formulário 2 — Segredo de Justiça

| Campo | PJe ID | Sim (suffix) | Não (suffix) | Default |
|-------|--------|--------------|--------------|---------|
| Segredo de Justiça | `frmSegredoSig:selectOneRadio` | `:0` | `:1` | **Não** |
| Botão Gravar sigilo | `frmSegredoSig:grvSegredo` | — | — | — |

#### Formulário 3 — Prioridade de Processo

| Campo | PJe ID | Tipo |
|-------|--------|------|
| Select Prioridade | `formAddPrioridadeProcesso:prioridadeProcesso:prioridadeProcessoDecoration:prioridadeProcesso` | `select` |
| Botão Incluir | `formAddPrioridadeProcesso:save` | `button` |

**Opções do select Prioridade (14 valores):**

| PJe value | Label PJe | Mapeamento Frontend (`prioridade[]`) |
|-----------|-----------|--------------------------------------|
| 413 | Art. 1048, II, do CPC (ECA) | `'ECA'` |
| 414 | Art. 1048, III, do CPC (Lei Maria da Penha) | `'MARIA_DA_PENHA'` |
| 415 | Art. 1048, IV, do CPC (Licitação) | `'LICITACAO'` |
| 416 | Art. 13 - Portaria Conjunta CNJ Nº 7 de 23/10/2023 | `'PORTARIA_CNJ_7'` |
| 417 | Art. 189-A, da Lei n. 11.101/2005 | `'LEI_11101'` |
| 418 | Art. 19, da Lei n. 9.507/1997 | `'LEI_9507'` |
| 419 | Art. 7o, parágrafo 4o, da Lei n. 12.016/2009 | `'LEI_12016'` |
| 420 | Idoso(a) | `'IDOSO'` |
| 421 | Idoso(a) maior de 80 anos | `'IDOSO_80'` |
| 422 | Pessoa com deficiência | `'PESSOA_DEFICIENCIA'` |
| 423 | Pessoa em situação de rua | `'PESSOA_SITUACAO_RUA'` |
| 424 | Portador(a) de doença grave | `'DOENCA_GRAVE'` |
| 425 | Réu Preso | `'REU_PRESO'` |

> **⚠ IMPORTANTE:** "Juízo 100% Digital" **NÃO é prioridade no PJe** — é um campo radio separado no Formulário 1. O frontend deve tratar como campo booleano independente (`juizoDigital`), não no array `prioridade[]`.

### Mapeamento PJe ↔ Frontend ↔ Backend

| Campo | PJe (tipo + form) | Frontend (campo `DadosBasicos`) | Backend (campo `DadosBasicos`) | Ação do Scraper |
|-------|-------------------|--------------------------------|-------------------------------|-----------------|
| Justiça Gratuita | Radio Sim/Não (Form 1) | `justicaGratuita: boolean` | `justica_gratuita: bool` | Click radio `:0` ou `:1` + Salvar |
| Juízo 100% Digital | Radio Sim/Não (Form 1) | `juizoDigital: boolean` | `juizo_digital: bool` | Click radio `:0` ou `:1` + Salvar |
| Pedido Liminar/Tutela | Radio Sim/Não (Form 1) | `pedidoLiminar: boolean` | `pedido_liminar: bool` | Click radio `:0` ou `:1` + Salvar |
| Valor da Causa | Text input (Form 1) | `valorCausa: number` | `valor_causa: float` | Fill input + Salvar |
| Segredo de Justiça | Radio Sim/Não (Form 2) | `nivelSigilo: number` (0=Não, ≥1=Sim) | `nivel_sigilo: int` | `nivelSigilo > 0` → Click `:0` (Sim), else `:1` (Não) + Gravar sigilo |
| Prioridade | Select + Incluir (Form 3) | `prioridade: string[]` | `prioridade: list[str]` | Para CADA item: set select value → Click Incluir |

> **Nota sobre o Scraper — 3 ações de salvamento separadas:**
> 1. Preencher Form 1 (Justiça Gratuita, Juízo Digital, Liminar, Valor) → click **Salvar**
> 2. Preencher Form 2 (Segredo de Justiça) → click **Gravar sigilo**
> 3. Para cada prioridade selecionada: selecionar no dropdown → click **Incluir** (repetir N vezes)

### Compatibilidade e Gaps

| Item | Status | Descrição |
|------|--------|-----------|
| Juízo 100% Digital | ⚠ **FIX NEEDED** | Frontend tinha como checkbox na seção "Prioridade". Deve ser campo booleano separado (`juizoDigital`). **→ Corrigido no código** |
| Prioridades incompletas | ⚠ **FIX NEEDED** | Frontend tinha apenas 4 opções (Juízo Digital, Idoso, Doença Grave, Criança). PJe tem 13 prioridades reais. **→ Expandido para todas 13** |
| CRIANÇA_ADOLESCENTE | ⚠ **Renomeado** | Não existe como label direto no PJe. Mapeia para value `413` "Art. 1048, II, do CPC (ECA)". **→ Renomeado para `ECA`** |
| Segredo de Justiça (níveis) | ✅ OK | Frontend usa dropdown 0-5 (MNI 2.2.2). Scraper mapeia: 0 → radio "Não", ≥1 → radio "Sim". PJe só mostra Sim/Não na UI, nível é enviado internamente pelo MNI |
| Justiça Gratuita | ✅ OK | RadioBool Sim/Não — compatível direto |
| Pedido Liminar/Tutela | ✅ OK | RadioBool Sim/Não — compatível direto |
| Valor da Causa | ✅ OK | Number input → text input PJe. Scraper formata para locale BRL |

### Fluxo de Automação (Scraper)

```python
# === STEP 4: Tab Características ===

# 1. Navegar para aba Características (se não já nela)
# await page.click('[ref do tab Características]')
# await asyncio.sleep(1)

# 2. FORMULÁRIO 1 — Características Principais
BASE = 'formAdicionarCaracteristicasProcesso'

# Justiça Gratuita (default: Não)
if dados.justica_gratuita:
    await page.click(f'[id="{BASE}:justicaGratuita:justicaGratuitaDecoration:justicaGratuitaSelectOneRadio:0"]')
# else: já default Não, não precisa clicar

# Juízo 100% Digital (default: nenhum marcado — OBRIGATÓRIO selecionar)
if dados.juizo_digital:
    await page.click(f'[id="{BASE}:solicitadoJuizo100PorCentoDigital:solicitadoJuizo100PorCentoDigitalDecoration:solicitadoJuizo100PorCentoDigitalSelectOneRadio:0"]')
else:
    await page.click(f'[id="{BASE}:solicitadoJuizo100PorCentoDigital:solicitadoJuizo100PorCentoDigitalDecoration:solicitadoJuizo100PorCentoDigitalSelectOneRadio:1"]')

# Pedido Liminar/Tutela (default: Não)
if dados.pedido_liminar:
    await page.click(f'[id="{BASE}:tutelaLiminar:tutelaLiminarDecoration:tutelaLiminarSelectOneRadio:0"]')

# Valor da Causa
if dados.valor_causa:
    campo_valor = f'{BASE}:valorCausa:valorCausaDecoration:valorCausa'
    await page.fill(f'[id="{campo_valor}"]', str(dados.valor_causa))

# SALVAR Form 1
await page.click(f'[id="{BASE}:salvaCaracteristicaProcessoButton"]')
await asyncio.sleep(1)  # aguardar A4J

# 3. FORMULÁRIO 2 — Segredo de Justiça
if dados.nivel_sigilo > 0:
    await page.click('[id="frmSegredoSig:selectOneRadio:0"]')  # Sim
else:
    await page.click('[id="frmSegredoSig:selectOneRadio:1"]')  # Não
await page.click('[id="frmSegredoSig:grvSegredo"]')
await asyncio.sleep(1)  # aguardar A4J

# 4. FORMULÁRIO 3 — Prioridades (repetir para cada)
PRIORIDADE_MAP = {
    'ECA': '413',
    'MARIA_DA_PENHA': '414',
    'LICITACAO': '415',
    'PORTARIA_CNJ_7': '416',
    'LEI_11101': '417',
    'LEI_9507': '418',
    'LEI_12016': '419',
    'IDOSO': '420',
    'IDOSO_80': '421',
    'PESSOA_DEFICIENCIA': '422',
    'PESSOA_SITUACAO_RUA': '423',
    'DOENCA_GRAVE': '424',
    'REU_PRESO': '425',
}

SELECT_ID = 'formAddPrioridadeProcesso:prioridadeProcesso:prioridadeProcessoDecoration:prioridadeProcesso'
BTN_INCLUIR = 'formAddPrioridadeProcesso:save'

for prio_key in dados.prioridade:
    pje_value = PRIORIDADE_MAP.get(prio_key)
    if pje_value:
        await page.evaluate(f"""
            const s = document.getElementById('{SELECT_ID}');
            s.value = '{pje_value}';
            s.dispatchEvent(new Event('change', {{bubbles: true}}));
        """)
        await asyncio.sleep(0.5)
        await page.click(f'[id="{BTN_INCLUIR}"]')
        await asyncio.sleep(1)  # aguardar A4J adicionar e limpar select

# Status: STEP 4 completo — avançar para tab=documento
```

### Valores preenchidos no processo de teste (`idProcesso=14112266`)

| Campo | Valor preenchido | Mensagem PJe |
|-------|-----------------|--------------|
| Justiça Gratuita? | **Sim** | "Registro alterado com sucesso." |
| Juízo 100% Digital? | **Sim** | (salvo junto com Form 1) |
| Pedido Liminar/Tutela? | **Sim** | (salvo junto com Form 1) |
| Valor da Causa (R$) | **R$ 1.000,00** | (salvo junto com Form 1) |
| Segredo de Justiça | **Não** (padrão) | "Registro alterado com sucesso" |
| Prioridade | **Idoso(a)** (value=420) | "Prioridade incluída com sucesso" |

> **Observação sobre o fluxo de Prioridade:** O dropdown do PJe é um RichFaces combobox (tree popup). Para selecionar: `page.get_by_role('combobox', name='Prioridade de processo').click()` → `page.get_by_role('treeitem', name='Idoso(a)').click()` → **Incluir**. Cada prioridade é adicionada individualmente (1 seleção + 1 clique em Incluir por vez). Após incluir, a prioridade aparece na tabela "Prioridade em processo" com ícone de lixeira para remover.

> **Observação sobre "Manter valor ao cadastrar":** Cada campo tem um ícone de cadeado 🔒 ("Manter valor ao cadastrar"). Quando ativado, o valor persiste em novas petições futuras do mesmo advogado. Não é obrigatório.

### Screenshots — Tab Características completa

- Formulários 1 + 2 + 3 preenchidos (visão superior): [page-caracteristicas-form1-top.png](../.playwright-mcp/page-caracteristicas-form1-top.png)
  - Justiça Gratuita=Sim, Juízo Digital=Sim, Liminar=Sim, Valor=R$ 1.000,00, Segredo=Não
- Prioridade "Idoso(a)" incluída + tabela com 1 resultado (visão inferior): [page-caracteristicas-completo.png](../.playwright-mcp/page-caracteristicas-completo.png)

> **Status: ✅ Tab Características COMPLETA — todos os campos preenchidos e salvos (3 formulários)**

### Arquivos do Código Fonte relacionados

| Arquivo | O que contém |
|---------|-------------|
| `frontend/components/peticoes/PeticaoFormCaracteristicas.tsx` | Componente React do formulário Características |
| `frontend/types/peticoes.ts` | Interface `DadosBasicos` com campos `juizoDigital`, `prioridade[]`, `nivelSigilo`, etc. |
| `backend/app/schemas/peticao.py` | Schema Pydantic `DadosBasicos` com `juizo_digital`, `prioridade`, `nivel_sigilo`, etc. |
| `backend/app/db/models/peticao.py` | Model: `dados_basicos_json` (JSONB) — armazena tudo como JSON |
| `backend/app/api/v1/endpoints/peticoes.py` | Endpoints `POST /peticoes`, `PATCH /peticoes/{id}` — serializa `dadosBasicos` → JSONB |
| `scraper/app/data/pje_cadastro_dados.py` | Dados de referência PJe (matérias, jurisdições) — adicionar `PRIORIDADE_MAP` |

---

## STEP 5 — Tab Documentos (`tab=documento`)

**URL:** `update.seam?idProcesso=14112266&tab=documento`

### Navegação

Navegar pela URL com `tab=documento` carrega a página mas mantém a aba anterior ativa.
É necessário clicar na aba "Incluir petições e documentos":

```
ref=e274  → cell "Incluir petições e documentos" (tab label)
```

### Estrutura da Aba

A aba tem dois sub-formulários:
1. **Sua petição** — documento principal (petição inicial)
2. **Anexos** — documentos adicionais opcionais

---

### Campo: Tipo de documento

| Propriedade | Valor |
|---|---|
| HTML ID | `cbTDDecoration:cbTD` |
| ref snapshot | `e309` (disabled) / `e312` (RichFaces input) |
| Tipo | `<select>` nativo (disabled) + RichFaces combobox visível |
| Valor padrão | `62` = "Petição inicial" |

> **Importante:** O campo está `disabled` no HTML nativo. É um combobox RichFaces. Para petição inicial o valor `62` já vem pré-selecionado e bloqueado. Para outros tipos de documento (peticão avulsa) o combobox fica habilitado.

**Opções completas do SELECT (82 entries):**
```
0  = Aditamento à inicial
1  = Alegações/Razões Finais
2  = Apelação
...
45 = Inicial
62 = Petição inicial  ← padrão bloqueado para processo inicial
63 = Petição intercorrente
65 = Procuração
66 = Procuração/Habilitação
81 = Substabelecimento
```
*(Ver lista completa extraída via JS: 82 opções de value 0 a 81 + "Selecione")*

---

### Campo: Descrição

| Propriedade | Valor |
|---|---|
| HTML ID | `ipDescDecoration:ipDesc` |
| ref snapshot | `e322` |
| Tipo | `<input type="text">` |
| Valor padrão | `"Petição inicial"` |

Editável. Aparece como título do documento na lista de peças.

---

### Campo: Número (opcional)

| Propriedade | Valor |
|---|---|
| HTML ID | `ipNroDecoration:ipNro` |
| ref snapshot | `e331` |
| Tipo | `<input type="text">` |
| Valor padrão | vazio |

---

### Campo: Sigiloso

| Propriedade | Valor |
|---|---|
| HTML ID | `sigDPCBDecoration:sigDPCB` |
| ref snapshot | `e339` |
| Tipo | `<input type="checkbox">` |
| Valor padrão | desmarcado |

---

### Campo: Tipo de arquivo — radio

| Opção | HTML ID | ref | Estado |
|---|---|---|---|
| Arquivo PDF | `raTipoDocPrincipal:0` | `e350` | checked (padrão) |
| Editor de texto | `raTipoDocPrincipal:1` | `e353` | desmarcado |

---

### Upload do PDF (Sua petição)

Com a opção "Arquivo PDF" selecionada, aparece a área de upload:

| Elemento | ref | Descrição |
|---|---|---|
| Drag-drop area + ADICIONAR | `e413` | clicável (abre file chooser) |
| **Choose File** botão | `e416` | clicável (abre file chooser nativo) |
| Input file | ID: `uploadDocumentoPrincipalDecoration:uploadDocumentoPrincipal:file` | input type=file oculto |

**Fluxo de upload:**
1. Clicar `e416` (Choose File) → abre file chooser nativo do SO
2. Selecionar arquivo PDF → ocorre submit automático via JS (multipart/form-data)
3. Página recarrega (Ajax partial render)
4. Arquivo aparece listado com nome + ícones de visualizar/excluir

**⚠️ Constraint de path no Playwright (Windows host):**
- Caminhos WSL (`/home/wital/...`) são rejeitados pelo Playwright rodando no Windows
- Solução: copiar arquivo para `/mnt/c/Users/wital/` (mapeado como `C:\Users\wital\`)
```bash
cp "docs/chamamento JOSE IRAN DE FIGUEIREDO.pdf" "/mnt/c/Users/wital/chamamento_JOSE_IRAN.pdf"
# Então usar: C:\Users\wital\chamamento_JOSE_IRAN.pdf
```

**Estado pós-upload:**
```
chamamento_JOSE_IRAN.pdf  [📄 ver]  [🗑️ excluir]
```

| Elemento pós-upload | ref | Descrição |
|---|---|---|
| Nome do arquivo (texto) | `e418` | texto simples |
| Ícone visualizar | `e419` | link, abre PDF |
| Ícone excluir | `e421` | link, remove o arquivo |

---

### Seção: Anexos (documentos adicionais)

Aparece abaixo da petição principal após o upload. Permite adicionar documentos extras (procuração, comprovantes, etc.).

| Elemento | ref | Descrição |
|---|---|---|
| **Adicionar** (link) | `e429` | abre novo upload para anexo |
| Arquivos suportados (link) | `e430` | abre modal com lista de formatos aceitos |

O fluxo de anexos é similar ao da petição principal (mesmo file chooser).

---

### Botão: ASSINAR DOCUMENTO(S)

| Propriedade | Valor |
|---|---|
| HTML ID | `btn-assinador` |
| ref snapshot | `e434` |
| Tipo | `<button>` |
| Texto | "Assinar documento(s)" |

Posição: canto inferior direito da seção de documentos.

**Comportamento ao clicar:**
- Aciona o assinador PJeOffice Pro (porta 8800 ou 8801)
- Modal de progresso aparece (`mpProgresso`)
- Se PJeOffice não estiver disponível: exibe modal `mpPJeOfficeIndisponivel`
- Quando assinatura concluída: avança para aba "Protocolar Inicial"

---

### Resumo de IDs — STEP 5

```python
DOCUMENTOS_IDS = {
    # Formulário principal
    "tipo_documento_select": "cbTDDecoration:cbTD",          # SELECT (disabled para petição inicial)
    "tipo_documento_combobox": "cbTDDecoration:cbTD_input",  # RichFaces input visível
    "descricao": "ipDescDecoration:ipDesc",
    "numero_opcional": "ipNroDecoration:ipNro",
    "sigiloso": "sigDPCBDecoration:sigDPCB",
    "radio_pdf": "raTipoDocPrincipal:0",                     # value="PDF"
    "radio_html": "raTipoDocPrincipal:1",                    # value="HTML"
    # Upload petição principal
    "file_input": "uploadDocumentoPrincipalDecoration:uploadDocumentoPrincipal:file",
    # Ações
    "btn_assinar": "btn-assinador",                          # "ASSINAR DOCUMENTO(S)"
}
# Valor "Petição inicial" = 62 no select
```

### Comportamento pós-clique ASSINAR

Após clicar em ASSINAR DOCUMENTO(S):

1. Modal "Por favor aguarde" aparece brevemente
2. PJe JS tenta conectar ao PJeOffice Pro via `http://localhost:8800`
   - ✅ PJeOffice disponível → abre UI de assinatura
   - ❌ PJeOffice indisponível → modal `mpPJeOfficeIndisponivel`
3. **O formulário é resetado** (Tipo=Selecione, Descrição=vazio — pronto para novo documento)
4. O documento fica salvo no servidor aguardando assinatura
5. O documento **APARECE na aba Protocolar** mesmo antes de ser assinado (mas não pode protocolar sem assinatura)

> **Warning Mixed Content:** Em browsers modernos, `http://localhost:8800` é bloqueado quando a página está em `https://`. PJeOffice Pro usa extensão de browser ou certificado especial para contornar.

---

---

## STEP 6 — Tab Protocolar (`tab=protocolar`)

**URL:** `update.seam?idProcesso=14112266&tab=protocolar`

### Navegação

Clicar na aba "Protocolar Inicial" (ref `e286`) ou via URL direta com `tab=protocolar`.
Pode ser acessada diretamente após completar os passos 1–5.

---

### Conteúdo do painel

#### Banner de Competência

Exibe automaticamente a competência definida pelo sistema com base na classe/assuntos:
```
ℹ Competência identificada para este processo:
  Cível (exceto Ambiental/Agrário)
```

---

#### Seção: Dados do processo

Resumo dos dados principais (preenchidos nas etapas anteriores):

| Campo | Valor (nosso exemplo) |
|---|---|
| Número do processo | *(vazio — gerado após protocolo)* |
| Jurisdição | Seção Judiciária da Bahia |
| Órgão julgador | *(vazio — distribuído após protocolo)* |
| Classe | MANDADO DE SEGURANÇA CÍVEL (120) |
| Data da distribuição | *(vazio — gerada após protocolo)* |
| Valor da causa | 1.000,00 |

---

#### Seção: Detalhes do processo

Mostra todas as partes, características e documentos:

**Assuntos:**
- Exame da Ordem OAB (10170)
- Anulação e Correção de Provas / Questões (10379)

**Polo Ativo:**
- ALEX SILVA MICIO DOS SANTOS - CPF: 677.541.805-10 (IMPETRANTE)
- 👤 AMANDA ALVES DE SOUSA - OAB CE50784 - CPF: 070.716.493-16 (ADVOGADO)

**Polo Passivo:**
- ORDEM DOS ADVOGADOS DO BRASIL CONSELHO FEDERAL - CNPJ: 33.205.451/0001-14 (TERCEIRO INTERESSADO)
- 🏛 Procuradoria do Conselho Federal da OAB
- .PRESIDENTE DO CONSELHO FEDERAL DA ORDEM DOS ADVOGADOS DO BRASIL (IMPETRADO)
- FUNDACAO GETULIO VARGAS - CNPJ: 33.641.663/0001-44 (TERCEIRO INTERESSADO)
- .PRESIDENTE DA FUNDAÇÃO GETÚLIO VARGAS (IMPETRADO)

**Outros Interessados:**
- MINISTERIO PUBLICO FEDERAL - MPF - CNPJ: 26.989.715/0001-02 (FISCAL DA LEI)
- 🏛 Procuradoria da República nos Estados e no Distrito Federal

**Características:**
| Campo | Valor |
|---|---|
| Segredo de justiça? | NÃO |
| Justiça gratuita? | SIM |
| Pedido de liminar ou antecipação de tutela? | SIM |
| Há pedido de juízo 100% digital? | SIM |

---

#### Seção: Documentos

Tabela com todos os documentos adicionados no STEP 5:

**Colunas:** Id | Id na origem | Número | Origem | Juntado em | Juntado por | Documento | Tipo | Guia de recolhimento | Motivo da isenção | Anexos

**Linha do documento uploadado (nosso exemplo):**
| Campo | Valor |
|---|---|
| Id | `2241064592` |
| Origem | 1º Grau |
| Juntado por | AMANDA ALVES DE SOUSA - POLO ATIVO - Advogado |
| Documento | Petição inicial |
| Tipo | Petição inicial |
| Arquivo | `chamamento_JOSE_IRAN.pdf` |

**Links por documento:**
```
Download:  /pje/Processo/update.seam?idBin=2157062935&numeroDocumento=e6cd...&nomeArqProcDocBin=chamamento_JOSE_IRAN.pdf&idProcessoDocumento=2241064592&...
Validar:   /pje/Processo/Consulta/validaDocumento.seam?idProcessoDocumento=2241064592&...
Excluir:   "#" (link js)
```

> **Observação:** O documento ficou salvo mesmo sem a assinatura PJeOffice ser concluída (Mixed Content bloqueou). O documento tem `idProcessoDocumento=2241064592`. Para protocolar com êxito, o documento deve estar assinado.

---

### Botão: PROTOCOLAR

| Propriedade | Valor |
|---|---|
| ref snapshot | `e772` |
| Tipo | `<button>` |
| Texto | "Protocolar" |

Posição: canto inferior direito do painel.

**Comportamento ao clicar:**
- Valida se todos os documentos obrigatórios foram **assinados** via PJeOffice
- Se não assinado: exibe erro/aviso "documento pendente de assinatura"
- Se assinado: submete o processo ao sistema PJe
  - Gera o **número CNJ** do processo (ex: 0000001-00.2026.4.01.3300)
  - Define `Órgão julgador` por sorteio/distribuição
  - Exibe confirmação de protocolo com número gerado
  - Processo passa a ser consultável publicamente

---

### Fluxo completo ASSINAR → PROTOCOLAR

```
[STEP 5] Usuario clica ASSINAR DOCUMENTO(S)
   ↓
PJe JS tenta conectar ao PJeOffice Pro (localhost:8800)
   ↓ (PJeOffice rodando)         ↓ (PJeOffice não rodando)
Modal de assinatura              Modal "PJeOffice Indisponível"
   ↓                             Erro: deve instalar/iniciar PJeOffice
Usuario assina (token/cert)
   ↓
Documento assinado digitalmente
Form reseta para novo documento
   ↓
[STEP 6] Usuario clica "Protocolar Inicial" tab
   ↓
Revisa todos os dados do processo
   ↓
Botão PROTOCOLAR (e772)
   ↓
Sistema gera número CNJ + distribui
   ↓
Confirmação de Protocolo com número do processo
```

---

### Pré-requisito: PJeOffice Pro

Para o fluxo funcionar em produção, o **PJeOffice Pro** deve estar:
1. Instalado localmente (download em: https://www.pje.jus.br/wiki/index.php/PJeOffice)
2. Rodando na porta **8800** (default) ou **8801** (fallback)
3. Com certificado digital configurado (ICP-Brasil A1 ou A3)

**Mixed Content warning em Playwright:** O Playwright (Chromium) bloqueia requests `http://localhost:8800` vindas de páginas `https://`. Em produção, o PJeOffice usa certificado especial ou extensão de browser para contornar isso.

---

### Screenshots capturados

- `page-protocolar.png` — aba Protocolar com dados do processo
- `page-protocolar-full.png` — página completa com tabela de documentos

---

### IDs relevantes — STEP 6

```python
PROTOCOLAR_IDS = {
    "btn_protocolar": "e772",  # snapshot ref (dinâmico)
    # Tabela de documentos
    "doc_id_campo": "2241064592",      # idProcessoDocumento
    "doc_bin_id": "2157062935",        # idBin para download
    "doc_download_url": "/pje/Processo/update.seam?idBin={idBin}&numeroDocumento={hash}&nomeArqProcDocBin={filename}&idProcessoDocumento={idProcessoDocumento}&...",
    "doc_validar_url": "/pje/Processo/Consulta/validaDocumento.seam?idProcessoDocumento={idProcessoDocumento}&...",
}
```

---

## Arquivo de Dados

Os dados coletados estão salvos em:
`scraper/app/data/pje_cadastro_dados.py`

Contém:
- `SELECT_IDS` — IDs dos 3 selects nativos
- `NO_SELECTION` — valor "Selecione" do Seam JSF
- `MATERIAS` — 26 matérias TPU/CNJ
- `JURISDICOES` — dict por tribunal (`trf1` completo, outros vazios pendentes)
- `get_materia_value(texto)` — busca value por texto
- `get_jurisdicao_value(tribunal_code, texto)` — busca value por tribunal+texto
- `get_jurisdicao_by_orgao(tribunal_code, orgao_cnj)` — infere jurisdição pelo código CNJ do órgão
- `CARACTERISTICAS_IDS` — IDs dos campos de características (justiça gratuita, juízo digital, etc.)
- `PRIORIDADE_MAP` — mapeamento de prioridades para values do PJe

---

## Automação Implementada (scraper)

**Última atualização:** 04/03/2026

### Arquitetura da chamada

```
Frontend (PeticaoForm)
  → Backend API (POST /peticoes)
    → Worker (peticao_protocolar.py)
      → scraper_client.protocolar_via_scraper(tipo_peticao="peticao_inicial", dados_basicos={...})
        → Scraper HTTP (POST /scrape/protocolar-peticao)
          → pje_peticionamento.protocolar_peticao_pje()
            → if tipo_peticao == "peticao_inicial":
                _fluxo_peticao_inicial()    ← 6 steps
              else:
                _navegar_para_processo()     ← petição avulsa (existente)
```

### Arquivos modificados

| Arquivo | Mudança |
|---------|---------|
| `scraper/app/schemas.py` | `DocumentoExtra` model + campos `tipo_peticao`, `dados_basicos`, `documentos_extras` em `ProtocolarPeticaoRequest` |
| `scraper/app/main.py` | Converte `documentos_extras` e passa novos campos para `protocolar_peticao_pje()` |
| `scraper/app/scrapers/pje_peticionamento.py` | Routing `tipo_peticao` + `_fluxo_peticao_inicial()` (6 steps) + 3 helpers de partes |
| `backend/app/core/services/scraper_client.py` | Params `tipo_peticao`, `dados_basicos`, `documentos_extras` em `protocolar_via_scraper()` |
| `backend/app/workers/tasks/peticao_protocolar.py` | Extrai `tipo_peticao`, `dados_basicos_json`, monta `documentos_extras` (base64) |
| `scraper/app/data/pje_cadastro_dados.py` | Dados de referência (SELECT_IDS, MATERIAS, JURISDICOES, etc.) — já existente |

### Dados esperados em `dados_basicos` (JSON)

```json
{
  "classeProcessual": "120",
  "codigoLocalidade": "3300",
  "valorCausa": "10000.00",
  "justicaGratuita": true,
  "juizoDigital": false,
  "pedidoLiminar": true,
  "nivelSigilo": 0,
  "prioridade": ["idoso"],
  "assuntos": [
    {"codigoNacional": "10170", "principal": true},
    {"codigoNacional": "10379", "principal": false}
  ],
  "polos": [
    {
      "polo": "AT",
      "partes": [
        {
          "nome": "FULANO DA SILVA",
          "tipoParte": "AUTOR",
          "tipoPessoa": "F",
          "numeroDocumentoPrincipal": "52376389100"
        }
      ]
    },
    {
      "polo": "PA",
      "partes": [
        {
          "nome": "ORDEM DOS ADVOGADOS DO BRASIL",
          "tipoParte": "IMPETRADO",
          "tipoPessoa": "J",
          "numeroDocumentoPrincipal": "33205451000114",
          "orgaoPublico": false
        },
        {
          "nome": "PRESIDENTE DO CONSELHO FEDERAL DA OAB",
          "tipoParte": "IMPETRADO",
          "tipoPessoa": "A"
        }
      ]
    }
  ]
}
```

### Step 1 — Navegação para `cadastrar.seam`

**Problema encontrado:** `page.goto(cadastrar_url)` retorna "Página não encontrada" — JSF/Seam não aceita navegação direta.

**Solução implementada — 3 tentativas em cascata:**

1. **Menu PJe**: Clica "Abrir menu" → "Processo" → submenu com href contendo `CadastroPeticaoInicial`
2. **goto direto** com `wait_until="networkidle"` (ao invés de `domcontentloaded`)
3. **`window.location.href`** via JS (preserva contexto JSF da sessão logada)

Após cada tentativa, verifica se o formulário carregou buscando o select de Matéria:
```javascript
!!document.getElementById('processoTrfForm:classeJudicial:j_id207:areaDireitoCombo')
```

Se nenhuma tentativa funcionar, retorna erro com screenshot para diagnóstico.

### Step 1 — Preenchimento dos selects (Matéria → Jurisdição → Classe)

Os 3 selects são **widgets RichFaces** com `<select>` nativo escondido. A cadeia A4J:

```
Matéria.change → (A4J ~3s) → Jurisdição options carregadas
Jurisdição.change → (A4J ~3s) → Classe Judicial options carregadas
```

Automação via JS:
```javascript
const el = document.getElementById(selectId);
el.value = value;
el.dispatchEvent(new Event('change', {bubbles: true}));
```

**Inferência de valores:**
- **Matéria**: Default `1861` (DIREITO ADMINISTRATIVO). TODO: inferir do primeiro assunto.
- **Jurisdição**: Infere via `get_jurisdicao_by_orgao("trf1", codigoLocalidade)`. Fallback: `1` (SJBA).
- **Classe**: Direto do `dados_basicos.classeProcessual` (ex: `120` = MANDADO DE SEGURANÇA).

### Step 3 — Partes: Órgão Público (Sim/Não)

**Fluxo Pessoa Jurídica — dois caminhos conforme `orgaoPublico`:**

| `orgaoPublico` | Fluxo | Campos | Botão final |
|---|---|---|---|
| **Sim** (default PJe) | Nome → Pesquisar → Tabela resultados → Radio → | `preCadastroPessoaFisica_nomePJ` | **Inserir** |
| **Não** | CNPJ → Pesquisar → Auto-preenche nome → | campo `cnpj` | **CONFIRMAR** → **Vincular Parte** |

**IDs dos radios Órgão Público:**
- Sim: `preCadastroPessoaFisicaForm:isOrgaoPublico1Decoration:isOrgaoPublico1SelectOneRadio:0` (value=`true`)
- Não: `preCadastroPessoaFisicaForm:isOrgaoPublico1Decoration:isOrgaoPublico1SelectOneRadio:1` (value=`false`)

**Decisão automática:** Se `parte.orgaoPublico` não fornecido, infere:
- Tem CNPJ → `orgaoPublico = false` (busca por CNPJ)
- Sem CNPJ → `orgaoPublico = true` (busca por nome)

### Step 3 — Tipos de pessoa (3 helpers)

| Tipo | Função | Fluxo |
|---|---|---|
| Pessoa Física (CPF) | `_adicionar_parte_pessoa_fisica()` | Radio Física → CPF → Pesquisar → PJe auto-preenche nome → Confirmar → Vincular |
| Pessoa Jurídica (CNPJ) | `_adicionar_parte_pessoa_juridica()` | Radio Jurídica → Órgão Público Sim/Não → (ver tabela acima) |
| Ente ou Autoridade | `_adicionar_parte_ente()` | Radio Ente → Autocomplete nome → Selecionar sugestão → Confirmar → Vincular |

### Step 5 — Assinatura de documentos

A assinatura usa o interceptor PJeOffice V3 já implementado em `_assinar_e_enviar()`:
- Intercepta `img.src` para `localhost:8800/pjeOffice/requisicao/`
- Extrai task `cnj.assinadorHash` com hashes dos PDFs
- Assina hashes com a chave privada do certificado A1 (MD5withRSA / ASN1)
- Faz POST do resultado assinado de volta ao PJe
- Injeta resposta GIF (width=1 = sucesso) via canvas

### Step 6 — Protocolar

O botão "Protocolar" (`e772`) **não** chama PJeOffice novamente. Apenas valida que os documentos foram assinados no Step 5 e submete o processo. Retorna o número CNJ do processo gerado.

**Nota:** Se os documentos não estiverem assinados, o PJe exibe erro "documento pendente de assinatura".
