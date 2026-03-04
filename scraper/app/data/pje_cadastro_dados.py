"""Dados estáticos para Cadastro de Processo Inicial no PJe.

Coletados via scraping em 04/03/2026 — TRF1 cadastrar.seam
IDs dos selects nativos (hidden atrás do widget RichFaces):
  - Matéria:    processoTrfForm:classeJudicial:j_id207:areaDireitoCombo
  - Jurisdição: processoTrfForm:classeJudicial:jurisdicaoComboDecoration:jurisdicaoCombo
  - Classe:     processoTrfForm:classeJudicial:classeJudicialComboDecoration:classeJudicialCombo

NOTA: Matéria e Classe Judicial são do TPU (CNJ) — iguais em todos os tribunais.
      Jurisdição é por tribunal (lista as Seções e Subseções sob aquele TRF/TJ).
"""

# ──────────────────────────────────────────────────────────────────
# IDs dos selects (constantes por instância PJe)
# ──────────────────────────────────────────────────────────────────

SELECT_IDS = {
    "materia": "processoTrfForm:classeJudicial:j_id207:areaDireitoCombo",
    "jurisdicao": "processoTrfForm:classeJudicial:jurisdicaoComboDecoration:jurisdicaoCombo",
    "classe": "processoTrfForm:classeJudicial:classeJudicialComboDecoration:classeJudicialCombo",
}

# Valor padrão "Selecione" do Seam JSF
NO_SELECTION = "org.jboss.seam.ui.NoSelectionConverter.noSelectionValue"

# ──────────────────────────────────────────────────────────────────
# Matérias (TPU/CNJ — iguais em todos os tribunais PJe)
# Coletado: TRF1, 04/03/2026
# ──────────────────────────────────────────────────────────────────

MATERIAS = [
    {"value": "1861", "text": "DIREITO ADMINISTRATIVO E OUTRAS MATÉRIAS DE DIREITO PÚBLICO"},
    {"value": "2015", "text": "DIREITO AMBIENTAL"},
    {"value": "3297", "text": "DIREITO ASSISTENCIAL"},
    {"value": "1137", "text": "DIREITO CIVIL > COISAS"},
    {"value": "1066", "text": "DIREITO CIVIL > EMPRESAS"},
    {"value": "915",  "text": "DIREITO CIVIL > FAMÍLIA"},
    {"value": "1061", "text": "DIREITO CIVIL > FATOS JURÍDICOS"},
    {"value": "954",  "text": "DIREITO CIVIL > OBRIGAÇÕES"},
    {"value": "1108", "text": "DIREITO CIVIL > PESSOAS JURÍDICAS"},
    {"value": "940",  "text": "DIREITO CIVIL > PESSOAS NATURAIS"},
    {"value": "1125", "text": "DIREITO CIVIL > RESPONSABILIDADE CIVIL"},
    {"value": "945",  "text": "DIREITO CIVIL > SUCESSÕES"},
    {"value": "1496", "text": "DIREITO DA CRIANÇA E DO ADOLESCENTE"},
    {"value": "3302", "text": "DIREITO DA SAÚDE"},
    {"value": "1215", "text": "DIREITO DO CONSUMIDOR"},
    {"value": "2820", "text": "DIREITO ELEITORAL"},
    {"value": "1340", "text": "DIREITO INTERNACIONAL"},
    {"value": "1192", "text": "DIREITO MARÍTIMO"},
    {"value": "328",  "text": "DIREITO PENAL"},
    {"value": "229",  "text": "DIREITO PREVIDENCIÁRIO"},
    {"value": "1382", "text": "DIREITO PROCESSUAL CIVIL E DO TRABALHO"},
    {"value": "1266", "text": "DIREITO PROCESSUAL PENAL"},
    {"value": "2",    "text": "DIREITO TRIBUTÁRIO"},
    {"value": "3560", "text": "DIREITO À EDUCAÇÃO"},
    {"value": "3221", "text": "QUESTÕES DE ALTA COMPLEXIDADE, GRANDE IMPACTO E REPERCUSSÃO"},
    {"value": "1365", "text": "REGISTROS PÚBLICOS"},
]

# ──────────────────────────────────────────────────────────────────
# Jurisdições por tribunal
# Cada entrada: {"value": "<int>", "text": "<nome>"}
# value é o índice interno do PJe (começa em 0)
# ──────────────────────────────────────────────────────────────────

JURISDICOES = {
    "trf1": [
        {"value": "0",  "text": "Núcleos de Justiça 4.0"},
        {"value": "1",  "text": "Seção Judiciária da Bahia"},
        {"value": "2",  "text": "Seção Judiciária de Goiás"},
        {"value": "3",  "text": "Seção Judiciária de Mato Grosso"},
        {"value": "4",  "text": "Seção Judiciária de Rondônia"},
        {"value": "5",  "text": "Seção Judiciária de Roraima"},
        {"value": "6",  "text": "Seção Judiciária do Acre"},
        {"value": "7",  "text": "Seção Judiciária do Amapá"},
        {"value": "8",  "text": "Seção Judiciária do Amazonas"},
        {"value": "9",  "text": "Seção Judiciária do Distrito Federal"},
        {"value": "10", "text": "Seção Judiciária do Maranhão"},
        {"value": "11", "text": "Seção Judiciária do Pará"},
        {"value": "12", "text": "Seção Judiciária do Piauí"},
        {"value": "13", "text": "Seção Judiciária do Tocantins"},
        {"value": "14", "text": "Subseção Judiciária de Alagoinhas-BA"},
        {"value": "15", "text": "Subseção Judiciária de Altamira-PA"},
        {"value": "16", "text": "Subseção Judiciária de Anápolis-GO"},
        {"value": "17", "text": "Subseção Judiciária de Aparecida de Goiânia-GO"},
        {"value": "18", "text": "Subseção Judiciária de Araguaína-TO"},
        {"value": "19", "text": "Subseção Judiciária de Bacabal-MA"},
        {"value": "20", "text": "Subseção Judiciária de Balsas-MA"},
        {"value": "21", "text": "Subseção Judiciária de Barra do Garças-MT"},
        {"value": "22", "text": "Subseção Judiciária de Barreiras-BA"},
        {"value": "23", "text": "Subseção Judiciária de Bom Jesus da Lapa-BA"},
        {"value": "24", "text": "Subseção Judiciária de Campo Formoso-BA"},
        {"value": "25", "text": "Subseção Judiciária de Castanhal-PA"},
        {"value": "26", "text": "Subseção Judiciária de Caxias-MA"},
        {"value": "27", "text": "Subseção Judiciária de Corrente-PI"},
        {"value": "28", "text": "Subseção Judiciária de Cruzeiro do Sul-AC"},
        {"value": "29", "text": "Subseção Judiciária de Cáceres-MT"},
        {"value": "30", "text": "Subseção Judiciária de Diamantino-MT"},
        {"value": "31", "text": "Subseção Judiciária de Eunápolis-BA"},
        {"value": "32", "text": "Subseção Judiciária de Feira de Santana-BA"},
        {"value": "33", "text": "Subseção Judiciária de Floriano-PI"},
        {"value": "34", "text": "Subseção Judiciária de Formosa-GO"},
        {"value": "35", "text": "Subseção Judiciária de Guanambi-BA"},
        {"value": "36", "text": "Subseção Judiciária de Gurupi-TO"},
        {"value": "37", "text": "Subseção Judiciária de Ilhéus-BA"},
        {"value": "38", "text": "Subseção Judiciária de Imperatriz-MA"},
        {"value": "39", "text": "Subseção Judiciária de Irecê-BA"},
        {"value": "40", "text": "Subseção Judiciária de Itabuna-BA"},
        {"value": "41", "text": "Subseção Judiciária de Itaituba-PA"},
        {"value": "42", "text": "Subseção Judiciária de Itumbiara-GO"},
        {"value": "43", "text": "Subseção Judiciária de Jataí-GO"},
        {"value": "44", "text": "Subseção Judiciária de Jequié-BA"},
        {"value": "45", "text": "Subseção Judiciária de Ji-Paraná-RO"},
        {"value": "46", "text": "Subseção Judiciária de Juazeiro-BA"},
        {"value": "47", "text": "Subseção Judiciária de Juína-MT"},
        {"value": "48", "text": "Subseção Judiciária de Laranjal do Jari-AP"},
        {"value": "49", "text": "Subseção Judiciária de Luziânia-GO"},
        {"value": "50", "text": "Subseção Judiciária de Marabá-PA"},
        {"value": "51", "text": "Subseção Judiciária de Oiapoque-AP"},
        {"value": "52", "text": "Subseção Judiciária de Paragominas-PA"},
        {"value": "53", "text": "Subseção Judiciária de Parnaíba-PI"},
        {"value": "54", "text": "Subseção Judiciária de Paulo Afonso-BA"},
        {"value": "55", "text": "Subseção Judiciária de Picos-PI"},
        {"value": "56", "text": "Subseção Judiciária de Redenção-PA"},
        {"value": "57", "text": "Subseção Judiciária de Rio Verde-GO"},
        {"value": "58", "text": "Subseção Judiciária de Rondonópolis-MT"},
        {"value": "59", "text": "Subseção Judiciária de Santarém-PA"},
        {"value": "60", "text": "Subseção Judiciária de Sinop-MT"},
        {"value": "61", "text": "Subseção Judiciária de São Raimundo Nonato-PI"},
        {"value": "62", "text": "Subseção Judiciária de Tabatinga-AM"},
        {"value": "63", "text": "Subseção Judiciária de Teixeira de Freitas-BA"},
        {"value": "64", "text": "Subseção Judiciária de Tucuruí-PA"},
        {"value": "65", "text": "Subseção Judiciária de Uruaçu-GO"},
        {"value": "66", "text": "Subseção Judiciária de Vilhena-RO"},
        {"value": "67", "text": "Subseção Judiciária de Vitória da Conquista-BA"},
    ],
    # TRF3, TRF5, TRF6, TJCE — coletar via scraper/scripts/coletar_jurisdicoes.py
    "trf3": [],
    "trf5": [],
    "trf6": [],
    "tjce": [],
}


def get_materia_value(texto: str) -> str | None:
    """Busca value da Matéria por texto (exact ou partial, case-insensitive)."""
    texto_lower = texto.lower()
    for m in MATERIAS:
        if m["text"].lower() == texto_lower:
            return m["value"]
    for m in MATERIAS:
        if texto_lower in m["text"].lower():
            return m["value"]
    return None


def get_jurisdicao_value(tribunal_code: str, texto: str) -> str | None:
    """Busca value da Jurisdição por tribunal e texto (partial, case-insensitive)."""
    jurs = JURISDICOES.get(tribunal_code.lower(), [])
    texto_lower = texto.lower()
    for j in jurs:
        if j["text"].lower() == texto_lower:
            return j["value"]
    for j in jurs:
        if texto_lower in j["text"].lower():
            return j["value"]
    return None


def get_jurisdicao_by_orgao(tribunal_code: str, orgao_cnj: str) -> str | None:
    """Infere a Jurisdição a partir do código do órgão CNJ (últimos 4 dígitos do número do processo).

    Exemplos TRF1:
      orgao '3300' → Seção Judiciária da Bahia (value='1')
      orgao '3400' → Seção Judiciária de Goiás  (value='2')
      orgao '4100' → Seção Judiciária do Distrito Federal (value='9')

    Retorna None se não mapeado — usar get_jurisdicao_value com texto.
    """
    # Mapeamento código SJEF → value da jurisdição no PJe TRF1
    # Fonte: CSJT / CNPJ das Seções Judiciárias Federais
    _TRF1_ORGAO_MAP = {
        # Seções
        "3300": "1",   # SJBA — Salvador
        "3400": "2",   # SJGO — Goiânia
        "3500": "3",   # SJMT — Cuiabá
        "3600": "4",   # SJRO — Porto Velho
        "3700": "5",   # SJRR — Boa Vista
        "3800": "6",   # SJAC — Rio Branco
        "3900": "7",   # SJAP — Macapá
        "4000": "8",   # SJAM — Manaus
        "3200": "9",   # SJDF — Brasília
        "2200": "10",  # SJMA — São Luís
        "3100": "11",  # SJPA — Belém
        "4200": "12",  # SJPI — Teresina
        "4300": "13",  # SJTO — Palmas
    }
    return _TRF1_ORGAO_MAP.get(orgao_cnj)


# ─── PRIORIDADE DE PROCESSO (Tab Características) ───────────────────────
# Mapeamento: chave interna (usada no frontend/backend) → value do <select> PJe

PRIORIDADE_MAP: dict[str, str] = {
    "ECA": "413",                # Art. 1048, II, do CPC (ECA)
    "MARIA_DA_PENHA": "414",     # Art. 1048, III, do CPC (Lei Maria da Penha)
    "LICITACAO": "415",          # Art. 1048, IV, do CPC (Licitação)
    "PORTARIA_CNJ_7": "416",     # Art. 13 - Portaria Conjunta CNJ Nº 7 de 23/10/2023
    "LEI_11101": "417",          # Art. 189-A, da Lei n. 11.101/2005
    "LEI_9507": "418",           # Art. 19, da Lei n. 9.507/1997
    "LEI_12016": "419",          # Art. 7o, §4o, da Lei n. 12.016/2009
    "IDOSO": "420",              # Idoso(a)
    "IDOSO_80": "421",           # Idoso(a) maior de 80 anos
    "PESSOA_DEFICIENCIA": "422", # Pessoa com deficiência
    "PESSOA_SITUACAO_RUA": "423",# Pessoa em situação de rua
    "DOENCA_GRAVE": "424",       # Portador(a) de doença grave
    "REU_PRESO": "425",          # Réu Preso
}

# IDs PJe dos campos da tab Características (Formulário 1)
CARACTERISTICAS_IDS = {
    "justica_gratuita_sim": "formAdicionarCaracteristicasProcesso:justicaGratuita:justicaGratuitaDecoration:justicaGratuitaSelectOneRadio:0",
    "justica_gratuita_nao": "formAdicionarCaracteristicasProcesso:justicaGratuita:justicaGratuitaDecoration:justicaGratuitaSelectOneRadio:1",
    "juizo_digital_sim": "formAdicionarCaracteristicasProcesso:solicitadoJuizo100PorCentoDigital:solicitadoJuizo100PorCentoDigitalDecoration:solicitadoJuizo100PorCentoDigitalSelectOneRadio:0",
    "juizo_digital_nao": "formAdicionarCaracteristicasProcesso:solicitadoJuizo100PorCentoDigital:solicitadoJuizo100PorCentoDigitalDecoration:solicitadoJuizo100PorCentoDigitalSelectOneRadio:1",
    "liminar_sim": "formAdicionarCaracteristicasProcesso:tutelaLiminar:tutelaLiminarDecoration:tutelaLiminarSelectOneRadio:0",
    "liminar_nao": "formAdicionarCaracteristicasProcesso:tutelaLiminar:tutelaLiminarDecoration:tutelaLiminarSelectOneRadio:1",
    "valor_causa": "formAdicionarCaracteristicasProcesso:valorCausa:valorCausaDecoration:valorCausa",
    "btn_salvar": "formAdicionarCaracteristicasProcesso:salvaCaracteristicaProcessoButton",
    # Formulário 2 — Segredo de Justiça
    "segredo_sim": "frmSegredoSig:selectOneRadio:0",
    "segredo_nao": "frmSegredoSig:selectOneRadio:1",
    "btn_gravar_sigilo": "frmSegredoSig:grvSegredo",
    # Formulário 3 — Prioridade
    "select_prioridade": "formAddPrioridadeProcesso:prioridadeProcesso:prioridadeProcessoDecoration:prioridadeProcesso",
    "btn_incluir_prioridade": "formAddPrioridadeProcesso:save",
}


def get_prioridade_value(key: str) -> str | None:
    """Retorna o value PJe para uma chave de prioridade interna."""
    return PRIORIDADE_MAP.get(key)
