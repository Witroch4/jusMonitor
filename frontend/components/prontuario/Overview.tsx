'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useClient } from '@/hooks/api/useClients';
import { AlertCircle, TrendingUp, FileText, Clock } from 'lucide-react';

interface OverviewProps {
  clientId: string;
}

export default function Overview({ clientId }: OverviewProps) {
  const { data: client, isLoading: loading } = useClient(clientId);

  if (loading) {
    return (
      <div className="grid gap-6">
        <Card>
          <CardContent className="p-6">
            <div className="animate-pulse space-y-4">
              <div className="h-4 bg-gray-200 rounded w-3/4"></div>
              <div className="h-4 bg-gray-200 rounded w-1/2"></div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!client) {
    return (
      <Card>
        <CardContent className="p-6">
          <p className="text-muted-foreground">Cliente não encontrado</p>
        </CardContent>
      </Card>
    );
  }

  const healthScore = client.health_score || 75;
  const getHealthColor = (score: number) => {
    if (score >= 80) return 'text-green-600';
    if (score >= 60) return 'text-yellow-600';
    return 'text-red-600';
  };

  return (
    <div className="grid gap-6">
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 mt-2">
        {/* Resumo do Caso (Summary) - Left Column */}
        <div className="lg:col-span-4 space-y-6">
          <Card className="border-border/40 shadow-[0_8px_30px_rgb(0,0,0,0.04)] rounded-xl overflow-hidden hover:shadow-[0_8px_30px_rgb(0,0,0,0.08)] transition-all duration-300">
            <CardHeader className="border-b border-border/40 pb-4 bg-muted/10">
              <CardTitle className="font-serif text-xl tracking-tight text-primary">Resumo do Cliente</CardTitle>
            </CardHeader>
            <CardContent className="p-6">
              <div className="space-y-6">
                <div className="flex items-start gap-4">
                  <div className="p-2.5 rounded-full bg-primary/5 text-primary">
                    <AlertCircle className="w-5 h-5" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Nome</p>
                    <p className="font-serif font-semibold text-lg text-foreground mt-0.5">{client.full_name}</p>
                  </div>
                </div>

                <div className="flex items-start gap-4">
                  <div className="p-2.5 rounded-full bg-primary/5 text-primary">
                    <FileText className="w-5 h-5" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Documento</p>
                    <p className="font-medium text-foreground mt-0.5">{client.cpf_cnpj || 'Não cadastrado'}</p>
                  </div>
                </div>

                <div className="flex items-start gap-4">
                  <div className="p-2.5 rounded-full bg-primary/5 text-primary">
                    <Clock className="w-5 h-5" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Health Score</p>
                    <div className="mt-2 flex items-center gap-3">
                      <p className={`text-2xl font-bold ${getHealthColor(healthScore)}`}>
                        {healthScore}%
                      </p>
                      <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
                        <div
                          className={`h-full ${healthScore >= 80 ? 'bg-green-600' : healthScore >= 60 ? 'bg-yellow-600' : 'bg-red-600'
                            }`}
                          style={{ width: `${healthScore}%` }}
                        />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
        {/* Central Column: Interactions / Alerts */}
        <div className="lg:col-span-4 space-y-6">
          <Card className="border-border/40 shadow-[0_8px_30px_rgb(0,0,0,0.04)] rounded-xl overflow-hidden hover:shadow-[0_8px_30px_rgb(0,0,0,0.08)] transition-all duration-300 h-full flex flex-col">
            <CardHeader className="border-b border-border/40 pb-4 bg-muted/10">
              <CardTitle className="font-serif text-xl tracking-tight text-primary">Alertas e Recomendações</CardTitle>
            </CardHeader>
            <CardContent className="p-6 flex-1">
              <div className="relative pl-3 space-y-6">
                <div className="absolute left-[15px] top-4 bottom-4 w-px bg-border/60"></div>

                {client.alerts && client.alerts.length > 0 ? (
                  client.alerts.map((alert: any, index: number) => (
                    <div key={index} className="relative flex gap-5 group">
                      <div className="relative z-10 w-3.5 h-3.5 mt-1 rounded-full bg-primary border-[3px] border-background flex-shrink-0 shadow-sm group-hover:scale-125 transition-transform" />
                      <div className="flex-1">
                        <div className="flex items-start justify-between">
                          <h3 className="font-serif font-semibold text-lg leading-tight text-foreground">{alert.title}</h3>
                          <Badge variant={alert.priority === 'high' ? 'destructive' : 'secondary'} className="ml-2 shadow-sm font-medium">
                            {alert.priority}
                          </Badge>
                        </div>
                        <p className="text-sm font-medium text-muted-foreground mt-1.5 leading-relaxed">{alert.description}</p>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="relative flex gap-5 group">
                    <div className="relative z-10 w-3.5 h-3.5 mt-1 rounded-full bg-green-500 border-[3px] border-background flex-shrink-0 shadow-sm group-hover:scale-125 transition-transform" />
                    <div>
                      <h3 className="font-serif font-semibold text-lg leading-tight text-foreground">Status Positivo</h3>
                      <p className="text-sm font-medium text-muted-foreground mt-1.5 leading-relaxed">Não há alertas ou recomendações pendentes no momento.</p>
                    </div>
                  </div>
                )}
              </div>

              <div className="mt-8 pt-6 border-t border-border/40">
                <button className="w-full py-3 bg-primary hover:bg-primary/90 text-primary-foreground rounded-lg font-medium transition-all duration-300 shadow-md flex justify-center items-center gap-2">
                  Nova Interação
                  <span className="material-icons-outlined text-sm">add</span>
                </button>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right Column: KPIs & Fast Overview */}
        <div className="lg:col-span-4 space-y-6">
          <Card className="border-border/40 shadow-[0_8px_30px_rgb(0,0,0,0.04)] rounded-xl overflow-hidden hover:shadow-[0_8px_30px_rgb(0,0,0,0.08)] transition-all duration-300">
            <CardHeader className="border-b border-border/40 pb-4 bg-muted/10">
              <CardTitle className="font-serif text-xl tracking-tight text-primary">Próximos Passos</CardTitle>
            </CardHeader>
            <CardContent className="p-6">
              <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-4 flex items-center text-sm font-medium text-yellow-800 dark:text-yellow-500 shadow-sm">
                <AlertCircle className="mr-3 h-5 w-5" />
                <span>Atualização cadastral pendente</span>
              </div>
            </CardContent>
          </Card>

          <div className="grid gap-4">
            <Card className="border-border/40 shadow-sm rounded-xl overflow-hidden">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 p-5">
                <CardTitle className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Processos Ativos</CardTitle>
                <div className="p-1.5 rounded bg-primary/5"><FileText className="h-4 w-4 text-primary" /></div>
              </CardHeader>
              <CardContent className="p-5 pt-0">
                <div className="text-3xl font-serif font-bold">{client.active_cases_count || 0}</div>
                <p className="text-xs font-medium text-muted-foreground mt-1">De um total de {client.total_cases_count || 0}</p>
              </CardContent>
            </Card>

            <Card className="border-border/40 shadow-sm rounded-xl overflow-hidden">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 p-5">
                <CardTitle className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Última Interação</CardTitle>
                <div className="p-1.5 rounded bg-primary/5"><Clock className="h-4 w-4 text-primary" /></div>
              </CardHeader>
              <CardContent className="p-5 pt-0">
                <div className="text-2xl font-serif font-bold">
                  {client.last_interaction ? new Date(client.last_interaction).toLocaleDateString() : 'N/A'}
                </div>
                <p className="text-xs font-medium text-muted-foreground mt-1">{client.last_interaction_type || 'Nenhuma interação registrada'}</p>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
