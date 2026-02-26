# JusMonitor Frontend

Frontend web application para o sistema JusMonitor CRM Orquestrador.

## Stack Tecnológica

- **Next.js 14** - Framework React com App Router
- **TypeScript** - Tipagem estática
- **Tailwind CSS** - Estilização utility-first
- **Shadcn/UI** - Componentes UI acessíveis
- **React Query** - Gerenciamento de estado do servidor
- **Zustand** - Gerenciamento de estado global
- **Zod** - Validação de schemas

## Requisitos

- Node.js 20+
- npm ou yarn

## Instalação

```bash
# Instalar dependências
npm install

# Copiar arquivo de configuração
cp .env.example .env.local

# Editar .env.local com suas configurações
nano .env.local
```

## Desenvolvimento

```bash
# Rodar servidor de desenvolvimento
npm run dev

# Abrir http://localhost:3000
```

## Build

```bash
# Criar build de produção
npm run build

# Rodar build de produção
npm start
```

## Linting e Formatação

```bash
# ESLint
npm run lint

# Prettier
npm run format
```

## Estrutura do Projeto

```
frontend/
├── app/                  # App Router (Next.js 14)
│   ├── (auth)/          # Rotas de autenticação
│   ├── (dashboard)/     # Rotas do dashboard
│   ├── layout.tsx       # Layout raiz
│   └── page.tsx         # Página inicial
├── components/          # Componentes React
│   ├── ui/             # Componentes Shadcn/UI
│   └── ...             # Componentes customizados
├── lib/                # Utilitários e configurações
├── actions/            # Server Actions
├── hooks/              # Custom hooks
├── types/              # Definições de tipos TypeScript
└── public/             # Arquivos estáticos
```

## Variáveis de Ambiente

Veja `.env.example` para lista de variáveis necessárias.

Principal:
- `NEXT_PUBLIC_API_URL` - URL da API backend

## Componentes UI

Este projeto usa [Shadcn/UI](https://ui.shadcn.com/) para componentes base.

Para adicionar novos componentes:

```bash
npx shadcn-ui@latest add button
npx shadcn-ui@latest add card
# etc...
```

## Licença

Proprietário - JusMonitor
