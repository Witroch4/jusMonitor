# Guia de Correção: Sidebar Shadcn/UI + Tailwind v4

Este documento explica como resolver o bug onde a Sidebar do shadcn/ui não "empurra" o conteúdo da página, ficando sobreposta (overlay), especificamente em projetos que utilizam **Tailwind v4**.

## O Problema

No Tailwind v4, a configuração é feita diretamente no CSS via `@theme`. No entanto, se o arquivo `components.json` do seu projeto ainda apontar para um arquivo de configuração do Tailwind v3 (ex: `tailwind.config.ts`), o CLI do shadcn baixa a versão dos componentes compatível com o v3.

A versão v3 do componente `Sidebar` possui comportamentos de layout (como classes de z-index e posicionamento) que conflitam com o motor do Tailwind v4, resultando na barra lateral sobrepondo o conteúdo principal.

## Como Corrigir

### 1. Sincronizar o `components.json`
O CLI precisa saber que você está usando o Tailwind v4 puro. Para isso, o campo `tailwind.config` deve estar **vazio**.

Edite o seu `components.json`:
```json
{
  "tailwind": {
    "config": "",  // Deve estar vazio para Tailwind v4
    "css": "app/globals.css",
    "baseColor": "slate",
    "cssVariables": true
  }
}
```

### 2. Reinstalar o Componente Sidebar
Com a configuração corrigida, você deve forçar o CLI a baixar a versão correta (v4) do componente:

```bash
npx shadcn@latest add sidebar --overwrite
```

### 3. Ajustar o Layout (Lateral Inteira)
Para que a Sidebar ocupe a lateral inteira (sem o Header por cima), a estrutura no `layout.tsx` deve ser:

```tsx
<SidebarProvider>
  <Sidebar /> {/* Sem variant="inset" para ocupar a lateral toda */}
  <div className="flex flex-col min-h-svh w-full flex-1 min-w-0">
    <DashboardHeader />
    <SidebarInset>
      <main>{children}</main>
    </SidebarInset>
  </div>
</SidebarProvider>
```

### 4. Ajustes Manuais Necessários (Tailwind v4 Patch)

Em alguns casos, as classes arbitrárias do Tailwind v4 (ex: `w-[--sidebar-width]`) não são suficientes para forçar o Flexbox a empurrar o conteúdo. A solução definitiva envolve:

- **Impedir o Colapso**: Adicionar `shrink-0` no container principal da Sidebar no Desktop em `components/ui/sidebar.tsx`.
- **Largura Explícita (Style Prop)**: Forçar a largura via prop `style` no componente `Sidebar` (em `sidebar.tsx`), garantindo que tanto o "spacer" quanto a parte fixa tenham um valor numérico real:

```tsx
// Dentro de components/ui/sidebar.tsx
<div
  className="group peer hidden md:block shrink-0" // shrink-0 é essencial
  style={{
    width: state === "collapsed" ? SIDEBAR_WIDTH_ICON : SIDEBAR_WIDTH,
    ...props.style,
  }}
>
```

---
*Referência Técnica: [Blog do Elvio Barbosa sobre Shadcn + Tailwind v4](https://medium.com/@elviosousa/resolvendo-o-bug-de-layout-do-sidebar-do-shadcn-ui-com-tailwind-v4-abc)*
