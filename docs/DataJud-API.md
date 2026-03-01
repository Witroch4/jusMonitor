# 📚 Documentação: API Pública do Datajud

A **API Pública do Datajud** é uma ferramenta que disponibiliza acesso aos metadados de processos públicos de tribunais do judiciário brasileiro, baseada na Portaria Nº 160 de 09/09/2020.

## 🔐 Autenticação (API Key)

A autenticação é feita via **Chave Pública** no cabeçalho (header) das requisições.

> **Atenção:** Por razões de segurança, o CNJ pode alterar esta chave a qualquer momento. Verifique sempre a versão mais recente na Wiki oficial.

**Formato do Header:**
`Authorization: APIKey [Chave Pública]`

**Chave Atual:**

```http
Authorization: APIKey cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw==

```

---

## 🌐 Endpoints e URLs

A URL base é `https://api-publica.datajud.cnj.jus.br/`. Para acessar os dados, você deve adicionar o **alias** do tribunal específico ao final da URL.

### 🏛️ Tribunais Superiores

| Tribunal | URL de Busca (_search) |
| --- | --- |
| Tribunal Superior do Trabalho | `.../api_publica_tst/_search` |
| Tribunal Superior Eleitoral | `.../api_publica_tse/_search` |
| Tribunal Superior de Justiça | `.../api_publica_stj/_search` |
| Tribunal Superior Militar | `.../api_publica_stm/_search` |

### ⚖️ Justiça Federal

| Tribunal | URL de Busca (_search) |
| --- | --- |
| TRF 1ª Região | `.../api_publica_trf1/_search` |
| TRF 2ª Região | `.../api_publica_trf2/_search` |
| TRF 3ª Região | `.../api_publica_trf3/_search` |
| TRF 4ª Região | `.../api_publica_trf4/_search` |
| TRF 5ª Região | `.../api_publica_trf5/_search` |
| TRF 6ª Região | `.../api_publica_trf6/_search` |

### 🏙️ Justiça Estadual (Exemplos)

| Tribunal | URL de Busca (_search) |
| --- | --- |
| TJ Acre (TJAC) | `.../api_publica_tjac/_search` |
| TJ Ceará (TJCE) | `.../api_publica_tjce/_search` |
| TJ São Paulo (TJSP) | `.../api_publica_tjsp/_search` |
| TJ Distrito Federal (TJDFT) | `.../api_publica_tjdft/_search` |

*(A lista completa segue o padrão `api_publica_tj[sigla-estado]`)*

---

## 🚀 Exemplos de Uso

### 1. Pesquisa por Número de Processo

Utilize o método **POST** para consultar uma numeração única (CNJ).

**Configuração da Requisição:**

* **Método:** `POST`
* **Headers:**
* `Authorization: APIKey cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw==`
* `Content-Type: application/json`



**Corpo (JSON - Query DSL):**

```json
{
    "query": {
        "match": {
            "numeroProcesso": "00008323520184013202"
        }
    }
}

```

### 2. Pesquisa por Classe e Órgão Julgador

Exemplo buscando "Execução Fiscal" (Classe 1116) na "Vara de Execução Fiscal do DF" (Órgão 13597).

**Corpo (JSON - Query DSL):**

```json
{
    "query": {
        "bool": {
            "must": [
                {"match": {"classe.codigo": 1116}},
                {"match": {"orgaoJulgador.codigo": 13597}}
            ]
        }
    }
}

```

---

## 📑 Paginação com `search_after`

Para grandes volumes de dados (acima de 10 registros), recomenda-se o uso do `search_after` para performance e eficiência.

1. **Primeira Consulta:** Defina o `size` e a ordenação (`sort`) pelo `@timestamp`.
2. **Captura do Ponteiro:** No JSON de resposta, pegue o valor dentro do array `"sort"` do **último** registro.
3. **Próxima Página:** Envie uma nova requisição incluindo o parâmetro `"search_after"` com o valor capturado.

**Exemplo de requisição para próxima página:**

```json
{
  "size": 100,
  "query": { ... },
  "sort": [{"@timestamp": {"order": "asc"}}],
  "search_after": [ 1681366085550 ]
}

```

---

## 📖 Glossário de Atributos

| Atributo | Tipo | Descrição |
| --- | --- | --- |
| `id` | text | Chave única: Tribunal_Classe_Grau_Orgao_Numero |
| `numeroProcesso` | text | Numeração Única CNJ (sem formatação) |
| `dataAjuizamento` | datetime | Data de início do processo |
| `classe.nome` | text | Descrição da Classe Processual (TPU) |
| `orgaoJulgador.nome` | text | Nome da serventia/vara |
| `movimentos` | array | Lista de movimentações processuais |
| `@timestamp` | datetime | Data da última atualização no índice |
