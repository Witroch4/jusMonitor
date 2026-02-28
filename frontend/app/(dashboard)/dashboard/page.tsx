'use client'

import React from 'react'

export default function DashboardPage() {
  return (
    <div className="w-full max-w-[1600px] mx-auto animate-in fade-in duration-500">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
        <div>
          <h2 className="font-display text-4xl text-foreground mb-1">Central Operacional</h2>
          <div className="flex items-center gap-2">
            <p className="text-lg font-medium text-foreground/80">Bom dia, Dr. Andrade</p>
            <span className="text-xs font-bold uppercase text-muted-foreground tracking-wider">
              SEGUNDA-FEIRA, 24 DE MAIO
            </span>
          </div>
        </div>
      </div>

      <div className="flex gap-4 mb-8 overflow-x-auto pb-2 no-scrollbar">
        <button className="flex shrink-0 items-center gap-2 px-4 py-2 bg-card border border-border rounded-xl text-sm font-medium text-foreground/80 hover:border-primary hover:text-primary transition-colors shadow-sm">
          <span>Período</span>
          <span className="material-symbols-outlined text-primary text-sm">calendar_month</span>
        </button>
        <button className="flex shrink-0 items-center gap-2 px-4 py-2 bg-card border border-border rounded-xl text-sm font-medium text-foreground/80 hover:border-primary hover:text-primary transition-colors shadow-sm">
          <span>Advogado Responsável</span>
          <span className="material-symbols-outlined text-muted-foreground text-sm">expand_more</span>
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
        <div className="bg-card p-6 rounded-2xl border-l-4 border-l-destructive shadow-sm border-y border-r border-border">
          <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-4">Ativos em Risco</p>
          <div className="flex items-baseline gap-3 mb-2">
            <h3 className="text-4xl font-display text-foreground">12</h3>
            <span className="text-xs font-semibold px-2 py-1 bg-destructive/10 text-destructive rounded-lg flex items-center gap-1">
              <span className="material-symbols-outlined text-[12px]">trending_up</span>
              +4.2%
            </span>
          </div>
        </div>

        <div className="bg-card p-6 rounded-2xl border-l-4 border-l-primary shadow-sm border-y border-r border-border">
          <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-4">Retorno Financeiro</p>
          <div className="flex items-baseline gap-3 mb-2">
            <h3 className="text-4xl font-display text-primary">R$ 42k</h3>
            <span className="text-xs font-semibold px-2 py-1 bg-primary/10 text-primary rounded-lg flex items-center gap-1">
              <span className="material-symbols-outlined text-[12px]">trending_up</span>
              +12%
            </span>
          </div>
        </div>

        <div className="bg-card p-6 rounded-2xl border-l-4 border-l-primary shadow-sm border-y border-r border-border">
          <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-4">Novos Contratos</p>
          <div className="flex items-baseline gap-3 mb-2">
            <h3 className="text-4xl font-display text-foreground">5</h3>
            <span className="text-xs font-semibold px-2 py-1 bg-primary/10 text-primary rounded-lg flex items-center gap-1">
              <span className="material-symbols-outlined text-[12px]">trending_up</span>
              +8%
            </span>
          </div>
        </div>

        <div className="bg-card p-6 rounded-2xl border-l-4 border-l-primary shadow-sm border-y border-r border-border">
          <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-4">Audiências Próximas</p>
          <div className="flex items-baseline gap-3 mb-2">
            <h3 className="text-4xl font-display text-foreground">3</h3>
            <span className="text-xs font-semibold px-2 py-1 bg-secondary text-secondary-foreground rounded-lg">
              Esta semana
            </span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2">
          <div className="flex justify-between items-center mb-6">
            <h3 className="font-display text-2xl text-foreground">Atenção Imediata</h3>
            <a className="text-xs font-bold uppercase text-primary hover:underline flex items-center gap-1" href="#">
              Ver Todos <span className="material-symbols-outlined text-sm">chevron_right</span>
            </a>
          </div>

          <div className="bg-card rounded-2xl border border-border overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left whitespace-nowrap">
                <thead>
                  <tr className="text-[11px] font-bold text-muted-foreground uppercase tracking-wider border-b border-border bg-card">
                    <th className="px-6 py-4">Caso #</th>
                    <th className="px-6 py-4">Título</th>
                    <th className="px-6 py-4">Cliente</th>
                    <th className="px-6 py-4">Status</th>
                    <th className="px-6 py-4"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  <tr className="group hover:bg-muted/50 transition-colors">
                    <td className="px-6 py-4 text-sm text-muted-foreground">Caso 1</td>
                    <td className="px-6 py-4 text-sm font-medium text-foreground">#4829 - Recurso Especial</td>
                    <td className="px-6 py-4 text-sm text-foreground/70">Indústrias Matarazzo S.A.</td>
                    <td className="px-6 py-4">
                      <span className="px-2 py-1 bg-destructive/10 text-destructive text-[10px] font-bold rounded uppercase">
                        Prazo 2h
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button className="p-1 rounded-md border border-border text-primary hover:bg-primary/10 transition-colors">
                        <span className="material-symbols-outlined text-sm block">chevron_right</span>
                      </button>
                    </td>
                  </tr>
                  <tr className="bg-secondary/30 group hover:bg-muted/50 transition-colors">
                    <td className="px-6 py-4 text-sm text-muted-foreground">Caso 2</td>
                    <td className="px-6 py-4 text-sm font-medium text-foreground">#5102 - Contestação Civil</td>
                    <td className="px-6 py-4 text-sm text-foreground/70">Dr. Carlos Alberto</td>
                    <td className="px-6 py-4">
                      <span className="px-2 py-1 bg-destructive/10 text-destructive text-[10px] font-bold rounded uppercase">
                        Prazo 2h
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button className="p-1 rounded-md border border-border text-primary hover:bg-primary/10 transition-colors">
                        <span className="material-symbols-outlined text-sm block">chevron_right</span>
                      </button>
                    </td>
                  </tr>
                  <tr className="group hover:bg-muted/50 transition-colors">
                    <td className="px-6 py-4 text-sm text-muted-foreground">Caso 3</td>
                    <td className="px-6 py-4 text-sm font-medium text-foreground">#3912 - Agravo de Instrumento</td>
                    <td className="px-6 py-4 text-sm text-foreground/70">Construtora Aliança</td>
                    <td className="px-6 py-4">
                      <span className="px-2 py-1 bg-destructive/10 text-destructive text-[10px] font-bold rounded uppercase">
                        Prazo 4h
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button className="p-1 rounded-md border border-border text-primary hover:bg-primary/10 transition-colors">
                        <span className="material-symbols-outlined text-sm block">chevron_right</span>
                      </button>
                    </td>
                  </tr>
                  <tr className="bg-secondary/30 group hover:bg-muted/50 transition-colors">
                    <td className="px-6 py-4 text-sm text-muted-foreground">Caso 4</td>
                    <td className="px-6 py-4 text-sm font-medium text-foreground">#4401 - Embargos de Declaração</td>
                    <td className="px-6 py-4 text-sm text-foreground/70">Supermercados Vale</td>
                    <td className="px-6 py-4">
                      <span className="px-2 py-1 bg-destructive/10 text-destructive text-[10px] font-bold rounded uppercase animate-pulse">
                        Prazo 5h
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button className="p-1 rounded-md border border-border text-primary hover:bg-primary/10 transition-colors">
                        <span className="material-symbols-outlined text-sm block">chevron_right</span>
                      </button>
                    </td>
                  </tr>
                  <tr className="group hover:bg-muted/50 transition-colors">
                    <td className="px-6 py-4 text-sm text-muted-foreground">Caso 5</td>
                    <td className="px-6 py-4 text-sm font-medium text-foreground">#5022 - Ação Indenizatória</td>
                    <td className="px-6 py-4 text-sm text-foreground/70">Maria Socorro Santos</td>
                    <td className="px-6 py-4">
                      <span className="px-2 py-1 bg-destructive/10 text-destructive text-[10px] font-bold rounded uppercase">
                        Prazo 6h
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button className="p-1 rounded-md border border-border text-primary hover:bg-primary/10 transition-colors">
                        <span className="material-symbols-outlined text-sm block">chevron_right</span>
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div>
          <div className="flex justify-between items-center mb-6">
            <h3 className="font-display text-2xl text-foreground">Decisões Favoráveis</h3>
            <a className="text-xs font-bold uppercase text-primary hover:underline" href="#">
              Histórico
            </a>
          </div>

          <div className="space-y-4">
            <div className="bg-card p-5 rounded-2xl border border-border flex items-center gap-4 group hover:shadow-md hover:bg-muted/30 transition-all cursor-pointer">
              <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center text-primary group-hover:scale-105 transition-transform">
                <span className="material-symbols-outlined">gavel</span>
              </div>
              <div className="flex-1">
                <h4 className="font-bold text-foreground text-sm leading-tight mb-1">Sentença Procedente</h4>
                <p className="text-xs text-muted-foreground">Processo nº 0012344-91.2023</p>
              </div>
              <div className="text-[10px] font-bold text-primary tracking-widest uppercase">Hoje</div>
            </div>

            <div className="bg-card p-5 rounded-2xl border border-border flex items-center gap-4 group hover:shadow-md hover:bg-muted/30 transition-all cursor-pointer">
              <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center text-primary group-hover:scale-105 transition-transform">
                <span className="material-symbols-outlined">gavel</span>
              </div>
              <div className="flex-1">
                <h4 className="font-bold text-foreground text-sm leading-tight mb-1">Sentença Procedente</h4>
                <p className="text-xs text-muted-foreground">Processo nº 0056788-12.2023</p>
              </div>
              <div className="text-[10px] font-bold text-primary tracking-widest uppercase">Ontem</div>
            </div>

            <div className="bg-card p-5 rounded-2xl border border-border flex items-center gap-4 group hover:shadow-md hover:bg-muted/30 transition-all cursor-pointer">
              <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center text-primary group-hover:scale-105 transition-transform">
                <span className="material-symbols-outlined">task_alt</span>
              </div>
              <div className="flex-1">
                <h4 className="font-bold text-foreground text-sm leading-tight mb-1">Liminar Concedida</h4>
                <p className="text-xs text-muted-foreground">Processo nº 0099412-44.2024</p>
              </div>
              <div className="text-[10px] font-bold text-primary tracking-widest uppercase">22 Mai</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
