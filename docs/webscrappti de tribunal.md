 O que foi feito:
Backend
Dependências: Adicionei playwright ^1.49.0 ao pyproject.toml

Docker: Instalei Chromium do Playwright no Dockerfile (playwright install chromium --with-deps)

Schemas (processo.py):

ConsultarOABRequest — recebe OAB número + UF
OABProcessoResumo — resumo de cada processo (número, classe, assunto, partes, movimentação)
ConsultarOABResponse — resposta com lista de processos
Serviço (oab_finder_service.py - NEW):

Usa Playwright async para abrir o site do TRF1
Preenche OAB número + UF
Clica "PESQUISAR"
Aguarda resultados e parseia a tabela
Retorna processos encontrados
Trata: captcha, timeout, sem resultados, erros
Endpoint (POST /processos/consultar-oab):

Chama o serviço de scraping
Requer autenticação (JWT)
Retorna resposta estruturada
Frontend
Types (processos.ts): Adicionei tipos OAB
Hook (useProcessos.ts): Adicionei useConsultarOAB()
Página (page.tsx):
Adicionei terceira aba: "OAB Finder (web)"
Formulário: input OAB número + select UF (27 estados)
Tabela de resultados com: Processo, Classe/Assunto, Partes, Última Movimentação
Estados: vazio, buscando, com resultados, sem resultados, erro
Build
✅ Docker build passou com sucesso
✅ Backend está rodando


Update Todos

Add playwright dependency to pyproject.toml + Dockerfile

Add OAB Finder schemas to processo.py

Create oab_finder_service.py (Playwright scraping)

Add /consultar-oab endpoint to processos.py

Add OAB types to frontend/types/processos.ts

Add useConsultarOAB hook

Add OAB Finder tab to processos page